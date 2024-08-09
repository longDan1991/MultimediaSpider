import argparse

import config
import constant


async def parse_cmd():
    # 读取command arg
    parser = argparse.ArgumentParser(description='Media crawler program.')
    parser.add_argument('--platform', type=str, help='Media platform select (xhs | dy | ks | bili | wb | tieba)',
                        choices=[
                            constant.XHS_PLATFORM_NAME,
                            constant.DOUYIN_PLATFORM_NAME,
                            constant.KUAISHOU_PLATFORM_NAME,
                            constant.WEIBO_PLATFORM_NAME,
                            constant.BILIBILI_PLATFORM_NAME,
                            constant.TIEBA_PLATFORM_NAME
                        ], default=config.PLATFORM)
    parser.add_argument('--type', type=str, help='crawler type (search | detail | creator)',
                        choices=["search", "detail", "creator"], default=config.CRAWLER_TYPE)
    parser.add_argument('--keywords', type=str,
                        help='please input keywords', default=config.KEYWORDS)
    parser.add_argument('--start', type=int,
                        help='number of start page', default=config.START_PAGE)
    parser.add_argument('--save_data_option', type=str,
                        help='where to save the data (csv or db or json)', choices=['csv', 'db', 'json'],
                        default=config.SAVE_DATA_OPTION)

    args = parser.parse_args()

    # override config
    config.PLATFORM = args.platform
    config.CRAWLER_TYPE = args.type
    config.START_PAGE = args.start
    config.KEYWORDS = args.keywords
