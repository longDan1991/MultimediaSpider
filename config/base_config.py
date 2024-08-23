# 基础配置
import os
from typing import List

from constant import EXCEL_ACCOUNT_SAVE

PLATFORM = "xhs"
KEYWORDS = "python,golang"

# 具体值参见media_platform.xxx.field下的枚举值，暂时只支持小红书
SORT_TYPE = "popularity_descending"

# 具体值参见media_platform.xxx.field下的枚举值，暂时只支持抖音
PUBLISH_TIME_TYPE = 0
CRAWLER_TYPE = "search"  # 爬取类型，search(关键词搜索) | detail(帖子详情)| creator(创作者主页数据)

# 数据保存类型选项配置,支持三种类型：csv、db、json
SAVE_DATA_OPTION = "db"  # csv or db or json

# 账号池保存类型选项配置,支持2种类型：xlsx、mysql
ACCOUNT_POOL_SAVE_TYPE = os.getenv("ACCOUNT_POOL_SAVE_TYPE", EXCEL_ACCOUNT_SAVE)

# 爬取开始页数 默认从第一页开始
START_PAGE = 1

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 40

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 4

# 是否开启爬评论模式, 默认不开启爬评论
ENABLE_GET_COMMENTS = True

# 是否开启爬二级评论模式, 默认不开启爬二级评论
ENABLE_GET_SUB_COMMENTS = False

# 指定小红书需要爬虫的笔记ID列表
XHS_SPECIFIED_ID_LIST = [
    "6672c38c000000001c02aeb4",
    # ........................
]

# 指定小红书创作者ID列表
XHS_CREATOR_ID_LIST = [
    "63e36c9a000000002703502b",
    # ........................
]

# 指定微博平台需要爬取的帖子列表
WEIBO_SPECIFIED_ID_LIST = [
    "4982041758140155",
    # ........................
]
# 指定weibo创作者ID列表
WEIBO_CREATOR_ID_LIST = [
    "5533390220",
    # ........................
]

# 指定贴吧需要爬取的帖子列表
TIEBA_SPECIFIED_ID_LIST: List[str] = [

]

# 指定贴吧名称列表，爬取该贴吧下的帖子
TIEBA_NAME_LIST: List[str] = [
    # "盗墓笔记"
]

# 指定bili创作者ID列表(这里是up主页面的ID)
BILI_CREATOR_ID_LIST = [
    "434377496",
    # ........................
]

# 指定B站平台需要爬取的视频bvid列表
BILI_SPECIFIED_ID_LIST = [
    "BV1d54y1g7db",
    "BV1Sz4y1U77N",
    "BV14Q4y1n7jz",
    # ........................
]

# 指定抖音需要爬取的ID列表
DY_SPECIFIED_ID_LIST = [
    "7280854932641664319",
    "7202432992642387233"
    # ........................
]

# 指定Dy创作者ID列表(sec_id)
DY_CREATOR_ID_LIST = [
    "MS4wLjABAAAATJPY7LAlaa5X-c8uNdWkvz0jUGgpw4eeXIwu_8BhvqE",
    # ........................
]


# 指定快手平台需要爬取的ID列表
KS_SPECIFIED_ID_LIST = [
    "3xf8enb8dbj6uig",
    "3x6zz972bchmvqe"
]

# 指定快手创作者ID列表
KS_CREATOR_ID_LIST = [
    "3x4sm73aye7jq7i",
    # ........................
]
