import asyncio
import random
from typing import Union, Dict
import json
import httpx
import execjs
from enum import Enum
from typing import NamedTuple

from tenacity import RetryError
from httpx import RequestError, Response
from management.proxies.proxy import get_proxy
import traceback
from urllib.parse import urlencode


class ErrorTuple(NamedTuple):
    code: int
    msg: str


class ErrorEnum(Enum):
    IP_BLOCK = ErrorTuple(300012, "网络连接异常，请检查网络设置或重启试试")
    NOTE_ABNORMAL = ErrorTuple(-510001, "笔记状态异常，请稍后查看")
    NOTE_SECRETE_FAULT = ErrorTuple(-510001, "当前内容无法展示")
    SIGN_FAULT = ErrorTuple(300015, "浏览器异常，请尝试关闭/卸载风险插件或重启试试！")
    SESSION_EXPIRED = ErrorTuple(-100, "登录已过期")
    ACCEESS_FREQUENCY_ERROR = ErrorTuple(300013, "访问频次异常，请勿频繁操作或重启试试")


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
        # await asyncio.sleep(random.randint(2, 10))
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
    except Exception as e:
        print(f"[request.post] 请求出错: {uri}")
        print(f"错误信息: {str(e)}")
        raise


async def get(uri: str, params=None, **kwargs) -> Union[Response, Dict]:
    final_uri = uri
    if isinstance(params, dict):
        final_uri = f"{uri}?" f"{urlencode(params)}"
    try:
        headers = await _pre_headers(final_uri)
        res = await request(
            method="GET", url=f"{_XHS_API_URL}{final_uri}", headers=headers, **kwargs
        )
        return res
    except Exception as e:
        print(f"[request.get] 请求出错: {uri}")
        print(f"错误信息: {str(e)}")
        raise
