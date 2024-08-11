# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2024/4/5 10:18
# @Desc    : 基础类型
import time
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ProviderNameEnum(Enum):
    JISHU_HTTP_PROVIDER: str = "jishuhttp"
    KUAI_DAILI_PROVIDER: str = "kuaidaili"


class IpInfoModel(BaseModel):
    """Unified IP model"""
    ip: str = Field(title="ip")
    port: int = Field(title="端口")
    user: str = Field(title="IP代理认证的用户名")
    protocol: str = Field(default="https://", title="代理IP的协议")
    password: str = Field(title="IP代理认证用户的密码")
    expired_time_ts: Optional[int] = Field(title="IP 过期时间")

    def format_httpx_proxy(self) -> Dict:
        """
        Get the httpx proxy dict
        Returns:

        """
        httpx_proxy = {
            f"{self.protocol}": f"http://{self.user}:{self.password}@{self.ip}:{self.port}"
        }
        return httpx_proxy

    @property
    def is_expired(self) -> bool:
        """
        Check if the IP is expired
        Returns:
            bool: True if the IP is expired, False otherwise
        """
        return self.expired_time_ts < int(time.time())