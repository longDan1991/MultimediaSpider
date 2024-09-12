import asyncio
from typing import Dict, List
from media_platform.douyin.field import SearchSortType
from media_platform.tieba.field import SearchNoteType
from models.tasks import Tasks, TaskDetails


async def search(task: Tasks) -> None:
    """
    根据任务搜索笔记并获取评论信息。
    """
    print("[XiaoHongShuCrawler.search] 开始搜索小红书关键词")
    xhs_limit_count = 20  # 小红书固定的每页限制数量
    task_details = TaskDetails(**task.data)

    if task_details.crawler_max_notes_count < xhs_limit_count:
        task_details.crawler_max_notes_count = xhs_limit_count

    for keyword in task_details.keywords.split(","):
        print(f"[XiaoHongShuCrawler.search] 当前搜索关键词: {keyword}")
        page = task_details.start_page
        while (
            page - task_details.start_page + 1
        ) * xhs_limit_count <= task_details.crawler_max_notes_count:
            try:
                print(
                    f"[XiaoHongShuCrawler.search] 搜索小红书关键词: {keyword}, 页码: {page}"
                )
                note_id_list: List[str] = []
                notes_res = await get_note_by_keyword(
                    keyword=keyword,
                    page=page,
                    sort=(
                        SearchSortType(task_details.sort_type)
                        if task_details.sort_type != ""
                        else SearchSortType.GENERAL
                    ),
                )
                print(f"[XiaoHongShuCrawler.search] 搜索笔记结果:{notes_res}")
                if not notes_res or not notes_res.get("has_more", False):
                    print("没有更多内容!")
                    break
                semaphore = asyncio.Semaphore(task_details.max_concurrency_num)
                task_list = [
                    get_note_detail(
                        note_id=post_item.get("id"),
                        xsec_source=post_item.get("xsec_source"),
                        xsec_token=post_item.get("xsec_token"),
                        semaphore=semaphore,
                    )
                    for post_item in notes_res.get("items", {})
                    if post_item.get("model_type") not in ("rec_query", "hot_query")
                ]
                note_details = await asyncio.gather(*task_list)
                for note_detail in note_details:
                    if note_detail:
                        # await xhs_store.update_xhs_note(note_detail)
                        note_id_list.append(note_detail.get("note_id", ""))
                page += 1
                print(f"[XiaoHongShuCrawler.search] 笔记详情: {note_details}")
                if task_details.enable_get_comments:
                    await batch_get_note_comments(note_id_list)

            except Exception as ex:
                print(f"[XiaoHongShuCrawler.search] 搜索笔记出错: {ex}")
                print(
                    "------------------------------------------记录当前爬取的关键词和页码------------------------------------------"
                )
                for i in range(10):
                    print(
                        f"[XiaoHongShuCrawler.search] 当前关键词: {keyword}, 页码: {page}"
                    )
                print(
                    "------------------------------------------记录当前爬取的关键词和页码---------------------------------------------------"
                )
                return


async def get_note_by_keyword(
    self,
    keyword: str,
    page: int = 1,
    page_size: int = 20,
    sort: SearchSortType = SearchSortType.GENERAL,
    note_type: SearchNoteType = SearchNoteType.ALL,
) -> Dict:
    """
    根据关键词搜索笔记
    Args:
        keyword: 关键词参数
        page: 分页第几页
        page_size: 分页数据长度
        sort: 搜索结果排序指定
        note_type: 搜索的笔记类型

    Returns:

    """
    uri = "/api/sns/web/v1/search/notes"
    data = {
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
        "search_id": get_search_id(),
        "sort": sort.value,
        "note_type": note_type.value,
    }
    return await self.post(uri, data)


async def get_note_detail(
    self, note_id: str, xsec_source: str, xsec_token: str, semaphore: asyncio.Semaphore
) -> Optional[Dict]:
    """
    Get note detail
    Args:
        note_id:
        xsec_source:
        xsec_token:
        semaphore:

    Returns:

    """
    async with semaphore:
        try:
            note_detail: Dict = await self.xhs_client.get_note_by_id(
                note_id, xsec_source, xsec_token
            )
            if not note_detail:
                utils.logger.error(
                    f"[XiaoHongShuCrawler.get_note_detail] Get note detail error, note_id: {note_id}"
                )
                return None
            note_detail.update({"xsec_token": xsec_token, "xsec_source": xsec_source})
            return note_detail
        except DataFetchError as ex:
            utils.logger.error(
                f"[XiaoHongShuCrawler.get_note_detail] Get note detail error: {ex}"
            )
            return None
        except KeyError as ex:
            utils.logger.error(
                f"[XiaoHongShuCrawler.get_note_detail] have not fund note detail note_id:{note_id}, err: {ex}"
            )
            return None


async def batch_get_note_comments(self, note_list: List[str]):
    """
    Batch get note comments
    Args:
        note_list:

    Returns:

    """
    if not config.ENABLE_GET_COMMENTS:
        utils.logger.info(
            f"[XiaoHongShuCrawler.batch_get_note_comments] Crawling comment mode is not enabled"
        )
        return

    utils.logger.info(
        f"[XiaoHongShuCrawler.batch_get_note_comments] Begin batch get note comments, note list: {note_list}"
    )
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
    task_list: List[Task] = []
    for note_id in note_list:
        task = asyncio.create_task(
            self.get_comments_async_task(note_id, semaphore), name=note_id
        )
        task_list.append(task)
    await asyncio.gather(*task_list)
