import asyncio
import random
from typing import Callable, Dict, List, Optional, Union

from httpx import RequestError, Response
from management.medium.xhs.request import post
from management.medium.xhs.utils.search_id import get_search_id
from media_platform.xhs.field import SearchSortType, SearchNoteType
from models.tasks import Tasks, TaskDetails
from pkg.tools import utils
import config


async def search(task: Tasks, cookies: str, callback: Optional[Callable] = None) -> None:
    """
    根据任务搜索笔记并获取评论信息。
    """
    utils.logger.info("[search] 开始搜索小红书关键词")
    page_size = 20  # 小红书固定的每页限制数量
    task_details = TaskDetails(**task.data)

    if task_details.crawler_max_notes_count < page_size:
        task_details.crawler_max_notes_count = page_size

    for keyword in task_details.keywords.split(","):
        utils.logger.info(f"[search] 当前搜索关键词: {keyword}")
        page = task_details.start_page
        while (page - task_details.start_page + 1) * page_size <= task_details.crawler_max_notes_count:
            try:
                utils.logger.info(f"[search] 搜索小红书关键词: {keyword}, 页码: {page}")
                note_ids: List[str] = []
                search_results = await get_notes_by_keyword(
                    keyword=keyword,
                    page=page,
                    sort=(
                        SearchSortType(task_details.sort_type)
                        if task_details.sort_type != ""
                        else SearchSortType.GENERAL
                    ),
                )
                utils.logger.info(f"[search] 搜索笔记结果:{search_results}")
                if not search_results or not search_results.get("has_more", False):
                    utils.logger.info("没有更多内容!")
                    break
                semaphore = asyncio.Semaphore(task_details.max_concurrency_num)
                tasks = [
                    get_note_detail(
                        note_id=item.get("id"),
                        xsec_source=item.get("xsec_source"),
                        xsec_token=item.get("xsec_token"),
                        semaphore=semaphore,
                    )
                    for item in search_results.get("items", {})
                    if item.get("model_type") not in ("rec_query", "hot_query")
                ]
                note_details = await asyncio.gather(*tasks)
                for note in note_details:
                    if note:
                        # 这里可以添加保存笔记详情的逻辑
                        if callback:
                            await callback(note)
                        note_ids.append(note.get("note_id", ""))
                page += 1
                utils.logger.info(f"[search] 笔记详情: {note_details}")
                if task_details.enable_get_comments:
                    await batch_get_note_comments(note_ids)

            except Exception as e:
                utils.logger.error(f"[search] 搜索笔记出错: {e}")
                utils.logger.error(f"[search] 当前关键词: {keyword}, 页码: {page}")
                return


async def get_notes_by_keyword(
    keyword: str,
    page: int = 1,
    page_size: int = 20,
    sort: SearchSortType = SearchSortType.GENERAL,
    note_type: SearchNoteType = SearchNoteType.ALL,
) -> Dict:
    """
    根据关键词搜索笔记
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
    return await post(uri, data)


async def get_note_detail(
    note_id: str, xsec_source: str, xsec_token: str, semaphore: asyncio.Semaphore
) -> Optional[Dict]:
    """
    获取笔记详情
    """
    async with semaphore:
        try:
            note_detail: Dict = await get_note_by_id(note_id, xsec_source, xsec_token)
            if not note_detail:
                utils.logger.error(f"[get_note_detail] 获取笔记详情失败, note_id: {note_id}")
                return None
            note_detail.update({"xsec_token": xsec_token, "xsec_source": xsec_source})
            return note_detail
        except RequestError as e:
            utils.logger.error(f"[get_note_detail] 获取笔记详情出错: {e}")
            return None
        except KeyError as e:
            utils.logger.error(f"[get_note_detail] 未找到笔记详情 note_id:{note_id}, 错误: {e}")
            return None


async def get_note_by_id(
    note_id: str, xsec_source: str = "", xsec_token: str = ""
) -> Dict:
    """
    获取笔记详情API
    """
    data = {
        "source_note_id": note_id,
        "image_formats": ["jpg", "webp", "avif"],
        "extra": {"need_body_topic": 1},
    }
    uri = "/api/sns/web/v1/feed"
    response = await post(uri, data)
    if response and response.get("items"):
        note_data: Dict = response["items"][0]["note_card"]
        return note_data
    utils.logger.error(f"[get_note_by_id] 获取笔记 id:{note_id} 为空，响应:{response}")
    return dict()


async def batch_get_note_comments(note_ids: List[str]):
    """
    批量获取笔记评论
    """
    utils.logger.info(f"[batch_get_note_comments] 开始批量获取笔记评论, 笔记列表: {note_ids}")
    semaphore = asyncio.Semaphore(1)
    tasks: List[asyncio.Task] = []
    for note_id in note_ids:
        task = asyncio.create_task(
            get_comments_async_task(note_id, semaphore), name=note_id
        )
        tasks.append(task)
    await asyncio.gather(*tasks)


async def get_comments_async_task(note_id: str, semaphore: asyncio.Semaphore):
    """
    异步获取笔记评论
    """
    async with semaphore:
        utils.logger.info(f"[get_comments_async_task] 开始获取笔记 {note_id} 的评论")
        await get_note_all_comments(
            note_id=note_id,
            crawl_interval=random.random(),
            callback=batch_update_xhs_note_comments,
        )


async def get_note_all_comments(
    note_id: str, crawl_interval: float = 1.0, callback: Optional[callable] = None
) -> List[Dict]:
    """
    获取指定笔记下的所有评论
    """
    result = []
    has_more = True
    cursor = ""
    while has_more:
        comments_data = await get_note_comments(note_id, cursor)
        has_more = comments_data.get("has_more", False)
        cursor = comments_data.get("cursor", "")
        if "comments" not in comments_data:
            utils.logger.info(f"[get_note_all_comments] 响应中没有 'comments' 键: {comments_data}")
            break
        comments = comments_data["comments"]
        if callback:
            await callback(note_id, comments)
        await asyncio.sleep(crawl_interval)
        result.extend(comments)
        if config.PER_NOTE_MAX_COMMENTS_COUNT and len(result) >= config.PER_NOTE_MAX_COMMENTS_COUNT:
            utils.logger.info(f"[get_note_all_comments] 评论数量超过限制: {config.PER_NOTE_MAX_COMMENTS_COUNT}")
            break
        sub_comments = await get_comments_all_sub_comments(comments, crawl_interval, callback)
        result.extend(sub_comments)
    return result


async def get_note_comments(note_id: str, cursor: str = "") -> Dict:
    uri = "/api/sns/web/v2/comment/page"
    params = {
        "note_id": note_id,
        "cursor": cursor,
        "top_comment_id": "",
        "image_formats": "jpg,webp,avif",
    }
    return dict({})  # await xhs_client.get(uri, params)


async def get_comments_all_sub_comments(
    comments: List[Dict],
    crawl_interval: float = 1.0,
    callback: Optional[Callable] = None,
) -> List[Dict]:
    result = []
    for comment in comments:
        note_id = comment.get("note_id")
        sub_comments = comment.get("sub_comments")
        if sub_comments and callback:
            await callback(note_id, sub_comments)

        has_more_sub_comments = comment.get("sub_comment_has_more")
        if not has_more_sub_comments:
            continue

        root_comment_id = comment.get("id")
        sub_comment_cursor = comment.get("sub_comment_cursor")

        while has_more_sub_comments:
            sub_comments_data = await get_note_sub_comments(
                note_id, root_comment_id, 10, sub_comment_cursor
            )
            has_more_sub_comments = sub_comments_data.get("has_more", False)
            sub_comment_cursor = sub_comments_data.get("cursor", "")
            if "comments" not in sub_comments_data:
                utils.logger.info(f"[get_comments_all_sub_comments] 响应中没有 'comments' 键: {sub_comments_data}")
                break
            sub_comments = sub_comments_data["comments"]
            if callback:
                await callback(note_id, sub_comments)
            await asyncio.sleep(crawl_interval)
            result.extend(sub_comments)
    return result


async def get_note_sub_comments(
    note_id: str, root_comment_id: str, num: int = 10, cursor: str = ""
):
    """
    获取指定父评论下的子评论的API
    Args:
        note_id: 子评论的帖子ID
        root_comment_id: 根评论ID
        num: 分页数量
        cursor: 分页游标

    Returns:

    """
    uri = "/api/sns/web/v2/comment/sub/page"
    params = {
        "note_id": note_id,
        "root_comment_id": root_comment_id,
        "num": num,
        "cursor": cursor,
    }
    return dict({})  # await xhs_client.get(uri, params)


async def batch_update_xhs_note_comments(note_id: str, comments: List[Dict]):
    # 这里需要实现批量更新笔记评论的逻辑
    # 可能需要调用数据库操作或其他服务
    utils.logger.info(f"更新笔记 {note_id} 的评论")
    # 示例：
    # await database.update_comments(note_id, comments)
