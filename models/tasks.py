from tortoise import Model, fields
from pydantic import BaseModel
from typing import List, Optional

from enum import Enum

class CrawlerType(Enum):
    SEARCH = "search"  # 关键词搜索
    DETAIL = "detail"  # 帖子详情
    CREATOR = "creator"  # 创作者主页数据

class Platform(Enum):
    XHS = "xhs"

class TaskDetails(BaseModel):
    keywords: Optional[str] = ""
    sort_type: Optional[str] = "popularity_descending"
    publish_time_type: Optional[int] = 0
    start_page: Optional[int] = 1
    crawler_max_notes_count: Optional[int] = 40
    max_concurrency_num: Optional[int] = 4
    enable_get_comments: Optional[bool] = True
    enable_get_sub_comments: Optional[bool] = False
    xhs_specified_id_list: Optional[List[str]] = []
    xhs_creator_id_list: Optional[List[str]] = []
    weibo_specified_id_list: Optional[List[str]] = []
    weibo_creator_id_list: Optional[List[str]] = []
    tieba_specified_id_list: Optional[List[str]] = []
    tieba_name_list: Optional[List[str]] = []
    tieba_creator_url_list: Optional[List[str]] = []
    bili_creator_id_list: Optional[List[str]] = []
    bili_specified_id_list: Optional[List[str]] = []
    dy_specified_id_list: Optional[List[str]] = []
    dy_creator_id_list: Optional[List[str]] = []
    ks_specified_id_list: Optional[List[str]] = []
    ks_creator_id_list: Optional[List[str]] = []


class Tasks(Model):
    id = fields.IntField(pk=True)
    platform = fields.CharField(max_length=50, default=Platform.XHS)
    crawler_type = fields.CharField(max_length=50, default=CrawlerType.SEARCH)
    data = fields.JSONField()
    

    class Meta:
        table = "tasks"
