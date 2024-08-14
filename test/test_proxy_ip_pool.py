# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 14:42
# @Desc    :
import asyncio
import time
from unittest import IsolatedAsyncioTestCase

from pkg.proxy.proxy_ip_pool import create_ip_pool
from pkg.proxy.types import IpInfoModel


class TestIpPool(IsolatedAsyncioTestCase):
    async def test_ip_pool(self):
        pool = await create_ip_pool(ip_pool_count=1, enable_validate_ip=True)
        print("\n")
        for i in range(3):
            ip_proxy_info: IpInfoModel = await pool.get_proxy()
            print(ip_proxy_info)
            print(f"当前ip {ip_proxy_info} 在多少时间后过期: {ip_proxy_info.expired_time_ts - int(time.time())} 秒")
            self.assertIsNotNone(ip_proxy_info.ip, msg="验证 ip 是否获取成功")
            await asyncio.sleep(1)



