
from pydantic import BaseModel
from typing import Optional, Dict
from enum import Enum

class Platform(Enum):
    XHS = "xhs"  # 小红书
    DOUYIN = "douyin"  # 抖音
    BILIBILI = "bilibili"  # bilibili
    KUAISHOU = "kuaishou"  # 快手
    TIEBA = "tieba"  # 贴吧
    WEIBO = "weibo"  # 微博

class PlatformStatus(BaseModel):
    max_page: Optional[int] = 11
    last_update: Optional[str] = ""
    last_page: Optional[int] = 0

PlatformInfo = Dict[Platform, PlatformStatus]
