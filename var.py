from contextvars import ContextVar

import aiomysql  # type: ignore

from async_db import AsyncMysqlDB

request_keyword_var: ContextVar[str] = ContextVar("request_keyword", default="")
crawler_type_var: ContextVar[str] = ContextVar("crawler_type", default="")
media_crawler_db_var: ContextVar[AsyncMysqlDB] = ContextVar("media_crawler_db_var")
db_conn_pool_var: ContextVar[aiomysql.Pool] = ContextVar("db_conn_pool_var")
source_keyword_var: ContextVar[str] = ContextVar("source_keyword", default="")