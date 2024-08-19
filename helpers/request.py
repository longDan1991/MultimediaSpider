# -*- coding: utf-8 -*-
from typing import Any, Dict, Union

import aiohttp
from pkg.tools import utils

SIGN_SERVER_URL = "http://localhost:8989"


async def request(method: str, uri: str, **kwargs) -> Union[Dict, Any]:
    """
    发送异步 HTTP 请求到指定的 URI，并返回响应数据。

    参数:
        method (str): HTTP 方法，如 'GET'、'POST' 等。
        uri (str): 请求的 URI，应是签名服务器的 URL 的一部分。
        **kwargs: 其他可能的参数，如 headers、data 等，将被传递给 aiohttp.request。

    返回:
        Union[Dict, Any]: 响应数据，通常是 JSON 格式（字典）或其他可以被解析为字典的格式。如果响应不是 JSON 格式，或者出现错误，将返回一个包含错误信息的字典，或者在极端情况下抛出异常。

    异常:
        Exception: 如果请求过程中发生错误，比如连接问题、请求超时、或者服务器返回非 200 状态码。

    使用示例:
        >>> try:
        >>>     response_data = await request('GET', '/api/resource')
        >>> except Exception as e:
        >>>     print(f"请求失败: {e}")
    """
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        ) as session:
            async with session.request(
                method, SIGN_SERVER_URL + uri, **kwargs
            ) as response:
                if response.status != 200:
                    response_text = await response.text()
                    utils.logger.error(
                        f"[helpers.request] response status code {response.status} response content: {response_text}"
                    )
                    raise Exception(f"请求签名服务器失败，状态码：{response.status}")

                data = await response.json()
                return data
    except Exception as e:
        raise Exception(f"请求签名服务器失败, error: {e}")
