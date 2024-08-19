# @Desc    : 快代理官方文档：https://www.kuaidaili.com/?ref=ldwkjqipvz6c

import httpx
import config
from tools import utils
from typing import Tuple, List


def _parse_proxy_info(proxy_info: str) -> Tuple[str, int, int]:
    """
    解析代理信息字符串，返回IP地址、端口和过期时间戳。

    参数：
    proxy_info (str): 代理信息字符串，格式为 "IP:PORT,EXPIRE_TS"

    返回：
    Tuple[str, int, int]: 包含IP地址、端口和过期时间戳的元组

    异常：
    ValueError: 如果格式不正确，返回 None
    """

    try:
        ip_port, expire_ts = proxy_info.split(",")

        ip, port = ip_port.split(":")

        return ip, port, expire_ts

    except ValueError:
        return None


async def fetch_proxies(num: int) -> List[(str, int, int)]:
    """
    从快代理获取指定数量的代理信息

    参数:
        num (int): 要获取的代理数量

    返回:
        List[(str, int, int)]: 包含 IP、端口和过期时间的代理列表

    示例:
        >>> proxies = await fetch_proxies(10)
        >>> for proxy in proxies:
        >>>    print(proxy)
    """
    brand = "kuaidaili"
    host = "https://dps.kdlapi.com/"
    params = {
        "num": num,
        "secret_id": config.KDL_SECERT_ID,
        "signature": config.KDL_SIGNATURE,
        "pt": 1,
        "format": "json",
        "sep": 1,
        "f_et": 1,
    }

    ip_infos = []
    async with httpx.AsyncClient() as client:
        response = await client.get(host + "/api/getdps/", params=params)

        if response.status_code != 200:
            utils.logger.error(
                f"[{brand} fetch_proxies] statuc code not 200 and response.txt:{response.text}"
            )

        ip_response = response.json()
        if ip_response.get("code") != 0:
            utils.logger.error(
                f"[{brand} fetch_proxies] code not 0 and msg:{ip_response.get('msg')}"
            )

        proxy_list = ip_response.get("data", {}).get("proxy_list")
        for item in proxy_list:
            (ip, port, expire) = _parse_proxy_info(item)
            ip_infos.append((ip, port, expire))

    return ip_infos


def get_proxy_str(proxy: Tuple[str, int, int]) -> str:
    """
    将代理元组转换为字符串格式

    参数:
        proxy (Tuple[str, int, int]): 包含 IP 地址、端口号和过期时间的元组

    返回:
        str: 格式化后的代理字符串，包含用户名和密码（如果存在）

    使用示例:
        >>> proxy = ("127.0.0.1", 8080, 3600)
        >>> get_proxy_str(proxy)
    """
    user = config.KDL_USER_NAME
    pwd = config.KDL_USER_PWD

    if user and pwd:
        return f"http://{user}:{pwd}@{proxy[0]}:{proxy[1]}"
    return ""
