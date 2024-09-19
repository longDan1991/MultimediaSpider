import httpx

from pkg.tools import utils 


async def is_valid_proxy(proxy: str) -> bool:
    """
    校验给定的代理是否有效

    参数:
        proxy (str): 代理的字符串表示，形式为 IP:PORT

    返回:
        bool: 如果代理有效则返回 True，否则返回 False

    使用示例:
        >>> proxy = "127.0.0.1:8080"
        >>> await is_valid_proxy(proxy)
    """
    utils.logger.info(f"[check_proxy] testing {proxy} is it valid ")
    try:
        async with httpx.AsyncClient(proxies={"https": proxy}) as client:
            response = await client.get("https://echo.apifox.com/ip")
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        utils.logger.info(f"[check_proxy] testing {proxy} err: {e}")
        return False
