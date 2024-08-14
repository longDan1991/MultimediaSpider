# -*- coding: utf-8 -*-
from typing import Dict, List

from db import AsyncMysqlDB
from var import media_crawler_db_var


async def query_platform_accounts_cookies(platform_name: str, cookie_status: int = 0) -> List[Dict]:
    """
    根据指定平台名称查询账号cookies列表
    Args:
        platform_name: xhs | dy | ks | wb | bili | tieba
        cookie_status: 0: 正常状态 -1: 异常状态

    Returns:

    """
    async_db_conn: AsyncMysqlDB = media_crawler_db_var.get()
    sql: str = f"select * from crawler_cookies_account where platform_name = '{platform_name}' and status = {cookie_status}"
    return await async_db_conn.query(sql)
