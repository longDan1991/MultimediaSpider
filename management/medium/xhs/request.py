import asyncio
import random
from typing import Union, Dict
import json
import httpx
import execjs

from tenacity import RetryError
from httpx import RequestError, Response
from management.proxies.proxy import get_proxy
import traceback


from media_platform.xhs.exception import (
    ErrorEnum,
)

_XHS_API_URL = "https://edith.xiaohongshu.com"
_XHS_INDEX_URL = "https://www.xiaohongshu.com"
_XHS_SIGN_SERVER_URL = "http://localhost:8989"


_timeout = 10

_Xhs_Sign = execjs.compile(open("helpers/js/xhs.js", encoding="utf-8").read())


async def request(method, url, **kwargs) -> Union[Response, Dict]:
    # proxy = await get_proxy()
    # print("============proxy", proxy)
    need_return_ori_response: bool = kwargs.get("return_response", False)
    if "return_response" in kwargs:
        del kwargs["return_response"]

    # async with httpx.AsyncClient(proxies={"https://": proxy}) as client:
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, timeout=_timeout, **kwargs)

    if need_return_ori_response:
        return response

    try:
        data = response.json()
        print("=============data", data)
    except json.decoder.JSONDecodeError:
        return response

    if response.status_code == 471 or response.status_code == 461:
        # someday someone maybe will bypass captcha
        verify_type = response.headers["Verifytype"]
        verify_uuid = response.headers["Verifyuuid"]
        raise Exception(
            f"出现验证码，请求失败，Verifytype: {verify_type}，Verifyuuid: {verify_uuid}, Response: {response}"
        )
    elif data.get("success"):
        return data.get("data", data.get("success"))
    elif data.get("code") == ErrorEnum.IP_BLOCK.value.code:
        raise RequestError(ErrorEnum.IP_BLOCK.value.msg)
    elif data.get("code") == ErrorEnum.SIGN_FAULT.value.code:
        raise RequestError(ErrorEnum.SIGN_FAULT.value.msg)
    elif data.get("code") == ErrorEnum.ACCEESS_FREQUENCY_ERROR.value.code:
        # 访问频次异常, 再随机延时一下
        print(f"[XiaoHongShuClient.request] 访问频次异常，尝试随机延时一下...")
        await asyncio.sleep(random.randint(2, 10))
        raise RequestError(ErrorEnum.ACCEESS_FREQUENCY_ERROR.value.msg)
    else:
        raise RequestError(data)


async def _pre_headers(uri: str, cookies: str, data=None) -> Dict:
    result = _Xhs_Sign.call("sign", uri, data, cookies)
    h = {
        "X-S": result.get("x-s"),
        "X-T": result.get("x-t"),
        "x-S-Common": result.get("x-s-common"),
        "X-B3-Traceid": result.get("x-b3-traceid"),
    }
    h.update(
        {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Cookie": cookies,
            "origin": _XHS_INDEX_URL,
            "referer": _XHS_INDEX_URL,
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }
    )
    return h


async def post(uri: str, cookies: str, data: dict, **kwargs) -> Union[Dict, Response]:
    json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    try:
        headers = await _pre_headers(uri, cookies, data)
        print("============headers", headers)
        res = await request(
            method="POST",
            url=f"{_XHS_API_URL}{uri}",
            data=json_str,
            headers=headers,
            **kwargs,
        )
        return res
    except RetryError as e:
        # 获取原始异常
        original_exception = e.last_attempt.exception()
        traceback.print_exception(
            type(original_exception),
            original_exception,
            original_exception.__traceback__,
        )

        print(
            f"[XiaoHongShuClient.post] 重试了5次:{uri} 请求，均失败了，尝试更换账号与IP再次发起重试"
        )
        # 如果重试了5次次都还是异常了，那么尝试更换账号信息
        # await self.mark_account_invalid(self.account_info)
        # await self.update_account_info()
        # headers = await self._pre_headers(uri, data)
        # return await self.request(
        #     method="POST",
        #     url=f"{XHS_API_URL}{uri}",
        #     data=json_str,
        #     headers=headers,
        #     **kwargs,
        # )
