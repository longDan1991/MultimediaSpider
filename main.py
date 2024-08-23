import asyncio
import sys
from typing import Dict, Optional, Type

import cmd_arg
import config
import constant
import db
from base.base_crawler import AbstractCrawler
from media_platform.bilibili import BilibiliCrawler
from media_platform.douyin import DouYinCrawler
from media_platform.kuaishou import KuaiShouCrawler
from media_platform.tieba import TieBaCrawler
from media_platform.weibo import WeiboCrawler
from media_platform.xhs import XiaoHongShuCrawler


class CrawlerFactory:
    CRAWLERS: Dict[str, AbstractCrawler]= {
        constant.XHS_PLATFORM_NAME: XiaoHongShuCrawler,
        constant.WEIBO_PLATFORM_NAME: WeiboCrawler,
        constant.TIEBA_PLATFORM_NAME: TieBaCrawler,
        constant.BILIBILI_PLATFORM_NAME: BilibiliCrawler,
        constant.DOUYIN_PLATFORM_NAME: DouYinCrawler,
        constant.KUAISHOU_PLATFORM_NAME: KuaiShouCrawler
    }

    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        """
        Create a crawler instance by platform
        Args:
            platform:

        Returns:

        """
        crawler_class: Optional[Type[AbstractCrawler]] = CrawlerFactory.CRAWLERS.get(platform)
        if not crawler_class:
            raise ValueError("Invalid Media Platform Currently only supported xhs or dy or ks or bili ...")
        return crawler_class()


async def main():
    # parse cmd
    await cmd_arg.parse_cmd()

    # init db
    if config.SAVE_DATA_OPTION == "db":
        await db.init_db()

    crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
    await crawler.async_initialize()
    await crawler.start()

    if config.SAVE_DATA_OPTION == "db":
        await db.close()


if __name__ == '__main__':
    try:
        # asyncio.run(main())
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        sys.exit()
