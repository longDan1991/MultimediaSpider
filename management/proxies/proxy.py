import random
from typing import List, Tuple

from management.proxies.brand.fast import fetch_proxies, get_proxy_str
from management.proxies.check_proxy import is_valid_proxy
from pkg.tools import utils
from helpers.redis import redis_client

IpPoolCount = 2
BrandProxy = "kuaidaili"


def _get_keys(pattern: str) -> List[str]:
    """
    根据指定的模式获取 Redis 键的列表

    参数:
        pattern (str): 用于匹配键的模式

    返回:
        List[str]: 符合模式的键的列表

    使用示例:
        >>> get_keys("brand_*")
    """
    return [key.decode() for key in redis_client.keys(pattern)]


def _get_all_ip(brand: str) -> List[Tuple[str, int, int]]:
    """
    从Redis中获取指定品牌的所有尚未过期的IP信息

    参数:
        brand (str): 品牌名称

    返回:
        List[(str, str, int)]: 包含IP地址、端口和过期时间（以秒为单位）的元组列表

    使用示例:
        >>> get_all_ip("example_brand")
    """
    ip_list = []
    keys = _get_keys(f"{brand}_*")

    for key in keys:
        try:
            ttl = redis_client.ttl(key)
            if ttl > 0:
                new_expired = ttl
                _, ip, port = key.split("_")
                ip_list.append((ip, port, new_expired))
        except Exception as e:
            utils.logger.error(f"解析 {key} 对应的值失败：{e}")
            break
    return ip_list


def _get_using_ip() -> tuple[str, str, int]:
    """
    获取当前正在使用的 IP 信息

    返回:
        tuple[str, str, int]: 包含 IP、端口和过期时间(TTL)的元组。如果没有正在使用的IP或者获取失败，返回None

    使用示例:
        >>> get_using_ip()
        ("127.0.0.1", "8080", 3600)
        >>> get_using_ip() is None
        True
    """
    ttl = redis_client.ttl("using_proxy")
    if ttl > 0:
        value = redis_client.get("using_proxy")
        if value:
            ip, port = value.decode().split(":")
            return ip, port, ttl
    return None


async def get_proxy() -> str:
    """
    获取一个有效的代理IP地址，优先使用正在使用的代理，如果无效，从缓存中随机选择一个或从远程获取

    返回:
        str: 包含IP地址和端口的字符串

    使用示例:
        >>> await get_proxy()
    """
    using_proxy = _get_using_ip()
    if using_proxy:
        valid = await is_valid_proxy(get_proxy_str(using_proxy))
        if valid:
            return using_proxy

    all_cache_proxy = _get_all_ip(BrandProxy)
    if len(all_cache_proxy) > 0:
        p = random.choice(all_cache_proxy)
        ip_port = f"{p[0]}_{p[1]}"
        redis_client.set(f"using_proxy", ip_port, ex=p[2])
        redis_client.delete(f"{BrandProxy}_{ip_port}")
        return get_proxy_str(p)

    remote_proxy = await fetch_proxies(IpPoolCount)

    if len(remote_proxy) == 0:
        return None

    for item in remote_proxy[0:]:
        redis_client.set(f"{BrandProxy}_{item[0]}_{item[1]}", "", ex=item[2])
        break

    rp = remote_proxy[0]
    ip_port = f"{rp[0]}_{rp[1]}"
    redis_client.set(f"using_proxy", ip_port, ex=rp[2])

    return get_proxy_str(rp)
