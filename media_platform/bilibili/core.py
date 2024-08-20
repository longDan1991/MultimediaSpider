# -*- coding: utf-8 -*-
import asyncio
import random
from asyncio import Task
from typing import Dict, List, Optional

import config
import constant
from base.base_crawler import AbstractCrawler
from pkg.account_pool.pool import AccountWithIpPoolManager
from pkg.proxy.proxy_ip_pool import ProxyIpPool, create_ip_pool
from pkg.tools import utils
from repo.platform_save_data import bilibili as bilibili_store
from var import crawler_type_var

from .client import BilibiliClient
from .exception import DataFetchError
from .field import SearchOrderType


class BilibiliCrawler(AbstractCrawler):
    def __init__(self) -> None:
        self.bili_client = BilibiliClient()

    async def async_initialize(self) -> None:
        """
        Asynchronous Initialization
        Returns:

        """
        utils.logger.info("[BilibiliCrawler.async_initialize] Begin async initialize")

        # 账号池和IP池的初始化
        proxy_ip_pool: Optional[ProxyIpPool] = None
        if config.ENABLE_IP_PROXY:
            # bilibili对代理验证还行，可以选择长时长的IP，比如30分钟一个IP
            # 快代理：私密代理->按IP付费->专业版->IP有效时长为30分钟, 购买地址：https://www.kuaidaili.com/?ref=ldwkjqipvz6c
            proxy_ip_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)

        # 初始化账号池
        account_with_ip_pool = AccountWithIpPoolManager(
            platform_name=constant.BILIBILI_PLATFORM_NAME,
            account_save_type=config.ACCOUNT_POOL_SAVE_TYPE,
            proxy_ip_pool=proxy_ip_pool
        )
        await account_with_ip_pool.async_initialize()

        self.bili_client.account_with_ip_pool = account_with_ip_pool
        await self.bili_client.update_account_info()

        # 设置爬虫类型
        crawler_type_var.set(config.CRAWLER_TYPE)

    async def start(self):
        """
        Start the crawler
        Returns:

        """
        if not await self.bili_client.pong():
            utils.logger.error("[BilibiliCrawler.start] 登录态已经失效，请重新替换Cookies尝试")
            return

        if config.CRAWLER_TYPE == "search":
            # Search for video and retrieve their comment information.
            await self.search()
        elif config.CRAWLER_TYPE == "detail":
            # Get the information and comments of the specified post
            await self.get_specified_videos(config.BILI_SPECIFIED_ID_LIST)
        elif config.CRAWLER_TYPE == "creator":
            await self.get_creator_videos()
        else:
            pass
        utils.logger.info(
            "[BilibiliCrawler.start] Bilibili Crawler finished ...")

    async def search(self):
        """
        search bilibili video with keywords
        :return:
        """
        utils.logger.info("[BilibiliCrawler.search] Begin search bilibli keywords")
        bili_limit_count = 20  # bilibili limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < bili_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = bili_limit_count
        start_page = config.START_PAGE
        for keyword in config.KEYWORDS.split(","):
            utils.logger.info(f"[BilibiliCrawler.search] Current search keyword: {keyword}")
            page = 1
            while (page - start_page + 1) * bili_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(
                        f"[BilibiliCrawler.search] Skip page: {page}")
                    page += 1
                    continue

                try:
                    utils.logger.info(f"[BilibiliCrawler.search] search bilibili keyword: {keyword}, page: {page}")
                    video_id_list: List[str] = []
                    videos_res = await self.bili_client.search_video_by_keyword(
                        keyword=keyword,
                        page=page,
                        page_size=bili_limit_count,
                        order=SearchOrderType.DEFAULT,
                    )
                    video_list: List[Dict] = videos_res.get("result")
                    if not video_list:
                        utils.logger.info(f"[BilibiliCrawler.search] Search note list is empty")
                        break
                    utils.logger.info(f"[BilibiliCrawler.search] Video list len: {len(video_list)}")
                    semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
                    task_list = [
                        self.get_video_info_task(aid=video_item.get("aid"), bvid="", semaphore=semaphore)
                        for video_item in video_list if video_item.get("type") == "video"
                    ]
                    video_items = await asyncio.gather(*task_list)
                    for video_item in video_items:
                        if video_item:
                            video_id_list.append(video_item.get("View").get("aid"))
                            await bilibili_store.update_bilibili_video(video_item)
                    page += 1
                    await self.batch_get_video_comments(video_id_list)

                except Exception as ex:
                    utils.logger.error(f"[BilibiliCrawler.search] Search notes error: {ex}")
                    # 发生异常了，则打印当前爬取的关键词和页码，用于后续继续爬取
                    utils.logger.info(
                        "------------------------------------------记录当前爬取的关键词和页码------------------------------------------")
                    for i in range(10):
                        utils.logger.error(f"[BilibiliCrawler.search] Current keyword: {keyword}, page: {page}")
                    utils.logger.info(
                        "------------------------------------------记录当前爬取的关键词和页码---------------------------------------------------")
                    return

    async def batch_get_video_comments(self, video_id_list: List[str]):
        """
        batch get video comments
        :param video_id_list:
        :return:
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(
                f"[BilibiliCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        utils.logger.info(
            f"[BilibiliCrawler.batch_get_video_comments] video ids:{video_id_list}")
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list: List[Task] = []
        for video_id in video_id_list:
            task = asyncio.create_task(self.get_comments(video_id, semaphore), name=video_id)
            task_list.append(task)
        await asyncio.gather(*task_list)

    async def get_comments_async_task(self, video_id: str, semaphore: asyncio.Semaphore):
        """
        get comment for video id
        :param video_id:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                utils.logger.info(
                    f"[BilibiliCrawler.get_comments_async_task] begin get video_id: {video_id} comments ...")
                await self.bili_client.get_video_all_comments(
                    video_id=video_id,
                    crawl_interval=random.random(),
                    callback=bilibili_store.batch_update_bilibili_video_comments
                )
            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_comments_async_task] get video_id: {video_id} comment error: {ex}")
            except Exception as e:
                utils.logger.error(f"[BilibiliCrawler.get_comments_async_task] may be been blocked, err:{e}")

    async def get_creator_videos(self):
        """
        get creator videos
        Returns:

        """
        for creator_id in config.BILI_CREATOR_ID_LIST:
            creator_video_list = await self.bili_client.get_all_videos_by_creator(creator_id)
            video_bvids_list = [video.get("bvid") for video in creator_video_list]
            await self.get_specified_videos(video_bvids_list)

    async def get_specified_videos(self, bvids_list: List[str]):
        """
        get specified videos info
        :return:
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [
            self.get_video_info_task(aid=0, bvid=video_id, semaphore=semaphore) for video_id in
            bvids_list
        ]
        video_details = await asyncio.gather(*task_list)
        video_aids_list = []
        for video_detail in video_details:
            if video_detail:
                video_item_view: Dict = video_detail.get("View")
                video_aid: str = video_item_view.get("aid")
                if video_aid:
                    video_aids_list.append(video_aid)
                await bilibili_store.update_bilibili_video(video_detail)
        await self.batch_get_video_comments(video_aids_list)

    async def get_video_info_task(self, aid: int, bvid: str, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """
        Get video detail task
        :param aid:
        :param bvid:
        :param semaphore:
        :return:
        """
        async with semaphore:
            try:
                result = await self.bili_client.get_video_info(aid=aid, bvid=bvid)
                return result
            except DataFetchError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_info_task] Get video detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(
                    f"[BilibiliCrawler.get_video_info_task] have not fund note detail video_id:{bvid}, err: {ex}")
                return None
