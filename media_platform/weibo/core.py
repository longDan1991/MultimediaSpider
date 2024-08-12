# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/23 15:41
# @Desc    : 微博爬虫主流程代码
import asyncio
import random
from asyncio import Task
from typing import Dict, List, Optional

import config
import constant
from account_pool.pool import AccountWithIpPoolManager
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import ProxyIpPool, create_ip_pool
from store import weibo as weibo_store
from tools import utils
from var import crawler_type_var

from .client import WeiboClient
from .exception import DataFetchError
from .field import SearchType
from .help import filter_search_result_card


class WeiboCrawler(AbstractCrawler):

    def __init__(self):
        self.wb_client = WeiboClient()

    async def async_initialize(self) -> None:
        """
        Asynchronous Initialization
        Returns:

        """
        proxy_ip_pool: Optional[ProxyIpPool] = None
        if config.ENABLE_IP_PROXY:
            # weibo对代理验证中等，可以选择长时长的IP，比如1-5分钟一个IP
            # 快代理：私密代理->按IP付费->专业版->IP有效时长为1-5分钟, 购买地址：https://www.kuaidaili.com/?ref=ldwkjqipvz6c
            proxy_ip_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)

        self.wb_client.account_with_ip_pool = AccountWithIpPoolManager(
            platform_name=constant.WEIBO_PLATFORM_NAME,
            account_save_type=constant.EXCEL_ACCOUNT_SAVE,
            proxy_ip_pool=proxy_ip_pool
        )
        await self.wb_client.update_account_info()

        crawler_type_var.set(config.CRAWLER_TYPE)

    async def start(self):
        """
        Start the crawler
        Returns:

        """
        if not await self.wb_client.pong():
            utils.logger.error("[WeiboCrawler.start] 登录态已经失效，请重新替换Cookies尝试")
            return

        if config.CRAWLER_TYPE == "search":
            # Search for video and retrieve their comment information.
            await self.search()
        elif config.CRAWLER_TYPE == "detail":
            # Get the information and comments of the specified post
            await self.get_specified_notes()
        else:
            pass
        utils.logger.info("[WeiboCrawler.start] Weibo Crawler finished ...")

    async def search(self):
        """
        search weibo note with keywords
        :return:
        """
        utils.logger.info("[WeiboCrawler.search] Begin search weibo keywords")
        weibo_limit_count = 10  # weibo limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < weibo_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = weibo_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            utils.logger.info(f"[WeiboCrawler.search] Current search keyword: {keyword}")
            page = 1
            while (page - start_page + 1) * weibo_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[WeiboCrawler.search] Skip page: {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(f"[WeiboCrawler.search] search weibo keyword: {keyword}, page: {page}")
                    search_res = await self.wb_client.get_note_by_keyword(
                        keyword=keyword,
                        page=page,
                        search_type=SearchType.DEFAULT
                    )
                    note_id_list: List[str] = []
                    note_list = filter_search_result_card(search_res.get("cards", []))
                    for note_item in note_list:
                        if note_item:
                            mblog: Dict = note_item.get("mblog", {})
                            if mblog:
                                note_id_list.append(mblog.get("id", ""))
                                await weibo_store.update_weibo_note(note_item)

                    page += 1
                    await self.batch_get_notes_comments(note_id_list)

                except DataFetchError as ex:
                    utils.logger.error(f"[WeiboCrawler.search] Search notes error: {ex}")
                    break

                except Exception as ex:
                    utils.logger.error(f"[WeiboCrawler.search] Get note detail error: {ex}")
                    # 发生异常了，则打印当前爬取的关键词和页码，用于后续继续爬取
                    utils.logger.info(
                        "------------------------------------------记录当前爬取的关键词和页码------------------------------------------")
                    for i in range(50):
                        utils.logger.error(f"[WeiboCrawler.search] Current keyword: {keyword}, page: {page}")
                    utils.logger.info(
                        "------------------------------------------记录当前爬取的关键词和页码---------------------------------------------------")
                    return

    async def get_specified_notes(self):
        """
        get specified notes info
        Returns:

        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_note_info_task(note_id=note_id, semaphore=semaphore) for note_id in
            config.WEIBO_SPECIFIED_ID_LIST
        ]
        video_details = await asyncio.gather(*task_list)
        for note_item in video_details:
            if note_item:
                await weibo_store.update_weibo_note(note_item)
        await self.batch_get_notes_comments(config.WEIBO_SPECIFIED_ID_LIST)

    async def get_note_info_task(self, note_id: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """
        get note detail task
        Args:
            note_id:
            semaphore:

        Returns:

        """
        async with semaphore:
            try:
                result = await self.wb_client.get_note_info_by_id(note_id)
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[WeiboCrawler.get_note_info_task] Get note detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[WeiboCrawler.get_note_info_task] have not fund note detail note_id:{note_id}, err: {ex}")
                return None

    async def batch_get_notes_comments(self, note_id_list: List[str]):
        """
        batch get notes comments
        Args:
            note_id_list:

        Returns:

        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[WeiboCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(f"[WeiboCrawler.batch_get_notes_comments] note ids:{note_id_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for note_id in note_id_list:
            task = asyncio.create_task(self.get_note_comments(note_id, semaphore), name=note_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_note_comments(self, note_id: str, semaphore: asyncio.Semaphore):
        """
        get note comments by note id
        Args:
            note_id:
            semaphore:

        Returns:

        """
        async with semaphore:
            try:
                utils.logger.info(f"[WeiboCrawler.get_note_comments] begin get note_id: {note_id} comments ...")
                await self.wb_client.get_note_all_comments(
                    note_id=note_id,
                    crawl_interval=random.randint(1, 3),  # 微博对API的限流比较严重，所以延时提高一些
                    callback=weibo_store.batch_update_weibo_note_comments
                )
            except DataFetchError as ex:
                utils.logger.error(f"[WeiboCrawler.get_note_comments] get note_id: {note_id} comment error: {ex}")
            except Exception as e:
                utils.logger.error(f"[WeiboCrawler.get_note_comments] may be been blocked, err:{e}")
