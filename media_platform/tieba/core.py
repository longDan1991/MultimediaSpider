import asyncio
import random
from asyncio import Task
from typing import List, Optional

import config
import constant
from account_pool.pool import AccountWithIpPoolManager
from base.base_crawler import AbstractCrawler
from model.m_baidu_tieba import TiebaNote
from proxy.proxy_ip_pool import ProxyIpPool, create_ip_pool
from store import tieba as tieba_store
from tools import utils
from var import crawler_type_var

from .client import BaiduTieBaClient
from .field import SearchNoteType, SearchSortType


class TieBaCrawler(AbstractCrawler):

    def __init__(self) -> None:
        self.tieba_client = BaiduTieBaClient()

    async def async_initialize(self) -> None:
        """
        Asynchronous Initialization
        Returns:

        """
        proxy_ip_pool: Optional[ProxyIpPool] = None
        if config.ENABLE_IP_PROXY:
            # 百度贴吧的代理验证很严格,经过测试1分钟一个IP就会被封，所以百度这边购买IP选择短时长
            # 快代理：私密代理->按IP付费->专业版->IP有效时长为1分钟, 购买地址：https://www.kuaidaili.com/?ref=ldwkjqipvz6c
            proxy_ip_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)

        self.tieba_client.account_with_ip_pool = AccountWithIpPoolManager(
            platform_name=constant.TIEBA_PLATFORM_NAME,
            account_save_type=constant.EXCEL_ACCOUNT_SAVE,
            proxy_ip_pool=proxy_ip_pool
        )
        await self.tieba_client.update_account_info()

    async def start(self) -> None:
        """
        Start the crawler
        Returns:

        """
        crawler_type_var.set(config.CRAWLER_TYPE)
        if config.CRAWLER_TYPE == "search":
            # Search for notes and retrieve their comment information.
            await self.search()
            await self.get_specified_tieba_notes()
        elif config.CRAWLER_TYPE == "detail":
            # Get the information and comments of the specified post
            await self.get_specified_notes()
        else:
            pass

        utils.logger.info("[BaiduTieBaCrawler.start] Tieba Crawler finished ...")

    async def search(self) -> None:
        """
        Search for notes and retrieve their comment information.
        Returns:

        """
        utils.logger.info("[BaiduTieBaCrawler.search] Begin search baidu tieba keywords")
        tieba_limit_count = 10  # tieba limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < tieba_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = tieba_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            utils.logger.info(f"[BaiduTieBaCrawler.search] Current search keyword: {keyword}")
            page = 1
            while (page - start_page + 1) * tieba_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[BaiduTieBaCrawler.search] Skip page {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(f"[BaiduTieBaCrawler.search] search tieba keyword: {keyword}, page: {page}")
                    notes_list: List[TiebaNote] = await self.tieba_client.get_notes_by_keyword(
                        keyword=keyword,
                        page=page,
                        page_size=tieba_limit_count,
                        sort=SearchSortType.TIME_DESC,
                        note_type=SearchNoteType.FIXED_THREAD
                    )
                    if not notes_list:
                        utils.logger.info(f"[BaiduTieBaCrawler.search] Search note list is empty")
                        break
                    utils.logger.info(f"[BaiduTieBaCrawler.search] Note list len: {len(notes_list)}")
                    await self.get_specified_notes(note_id_list=[note_detail.note_id for note_detail in notes_list])
                    page += 1
                except Exception as ex:
                    utils.logger.error(f"[BaiduTieBaCrawler.search] Search notes error: {ex}")
                    # 发生异常了，则打印当前爬取的关键词和页码，用于后续继续爬取
                    utils.logger.info(
                        "------------------------------------------记录当前爬取的关键词和页码------------------------------------------")
                    for i in range(50):
                        utils.logger.error(f"[BaiduTieBaCrawler.search] Current keyword: {keyword}, page: {page}")
                    utils.logger.info(
                        "------------------------------------------记录当前爬取的关键词和页码---------------------------------------------------")
                    return

    async def get_specified_tieba_notes(self):
        """
        Get the information and comments of the specified post by tieba name
        Returns:

        """
        tieba_limit_count = 50
        if config.CRAWLER_MAX_NOTES_COUNT < tieba_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = tieba_limit_count
        for tieba_name in config.TIEBA_NAME_LIST:
            utils.logger.info(
                f"[BaiduTieBaCrawler.get_specified_tieba_notes] Begin get tieba name: {tieba_name}")
            page_number = 0
            while page_number <= config.CRAWLER_MAX_NOTES_COUNT:
                note_list: List[TiebaNote] = await self.tieba_client.get_notes_by_tieba_name(
                    tieba_name=tieba_name,
                    page_num=page_number
                )
                if not note_list:
                    utils.logger.info(
                        f"[BaiduTieBaCrawler.get_specified_tieba_notes] Get note list is empty")
                    break

                utils.logger.info(
                    f"[BaiduTieBaCrawler.get_specified_tieba_notes] tieba name: {tieba_name} note list len: {len(note_list)}")
                await self.get_specified_notes([note.note_id for note in note_list])
                page_number += tieba_limit_count

    async def get_specified_notes(self, note_id_list: List[str] = config.TIEBA_SPECIFIED_ID_LIST):
        """
        Get the information and comments of the specified post
        Args:
            note_id_list:

        Returns:

        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_detail_async_task(note_id=note_id, semaphore=semaphore) for note_id in note_id_list
        ]
        note_details = await asyncio.gather(*task_list)
        note_details_model: List[TiebaNote] = []
        for note_detail in note_details:
            if note_detail is not None:
                note_details_model.append(note_detail)
                await tieba_store.update_tieba_note(note_detail)
        await self.batch_get_note_comments(note_details_model)

    async def get_note_detail_async_task(self, note_id: str, semaphore: asyncio.Semaphore) -> Optional[TiebaNote]:
        """
        Get note detail
        Args:
            note_id: baidu tieba note id
            semaphore: asyncio semaphore

        Returns:

        """
        async with semaphore:
            try:
                utils.logger.info(f"[BaiduTieBaCrawler.get_note_detail] Begin get note detail, note_id: {note_id}")
                note_detail: TiebaNote = await self.tieba_client.get_note_by_id(note_id)
                if not note_detail:
                    utils.logger.error(
                        f"[BaiduTieBaCrawler.get_note_detail] Get note detail error, note_id: {note_id}")
                    return None
                return note_detail
            except Exception as ex:
                utils.logger.error(f"[BaiduTieBaCrawler.get_note_detail] Get note detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[BaiduTieBaCrawler.get_note_detail] have not fund note detail note_id:{note_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, note_detail_list: List[TiebaNote]):
        """
        Batch get note comments
        Args:
            note_detail_list:

        Returns:

        """
        if not config.ENABLE_GET_COMMENTS:
            return

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for note_detail in note_detail_list:
            task = asyncio.create_task(self.get_comments_async_task(note_detail, semaphore), name=note_detail.note_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments_async_task(self, note_detail: TiebaNote, semaphore: asyncio.Semaphore):
        """
        Get comments async task
        Args:
            note_detail:
            semaphore:

        Returns:

        """
        async with semaphore:
            utils.logger.info(f"[BaiduTieBaCrawler.get_comments] Begin get note id comments {note_detail.note_id}")
            await self.tieba_client.get_note_all_comments(
                note_detail=note_detail,
                crawl_interval=random.random(),
                callback=tieba_store.batch_update_tieba_note_comments
            )
