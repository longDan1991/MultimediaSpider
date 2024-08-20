from typing import Union, Dict
import json
from urllib.parse import urlencode
from helpers import request as _request
import httpx

from tenacity import RetryError, retry, stop_after_attempt, wait_fixed
from httpx import Response
from management.proxies.proxy import get_proxy
from tools import utils
import traceback

from ....media_platform.xhs.exception import (
    DataFetchError,
    ErrorEnum,
    IPBlockError,
    NeedVerifyError,
    SignError,
)

XHS_API_URL = "https://edith.xiaohongshu.com"
XHS_INDEX_URL = "https://www.xiaohongshu.com"
XHS_SIGN_SERVER_URL = "http://localhost:8989"

headers = {
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "Cookie": "",
    "origin": XHS_INDEX_URL,
    "referer": XHS_INDEX_URL,
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}


timeout = 10


async def request(method, url, **kwargs) -> Union[Response, Dict]:
    proxy = await get_proxy()
    need_return_ori_response: bool = kwargs.get("return_response", False)
    if "return_response" in kwargs:
        del kwargs["return_response"]

    async with httpx.AsyncClient(proxies={"https://": proxy}) as client:
        response = await client.request(method, url, timeout=timeout, **kwargs)

    if need_return_ori_response:
        return response

    try:
        data = response.json()
    except json.decoder.JSONDecodeError:
        return response

    if response.status_code == 471 or response.status_code == 461:
        # someday someone maybe will bypass captcha
        verify_type = response.headers["Verifytype"]
        verify_uuid = response.headers["Verifyuuid"]
        raise NeedVerifyError(
            f"出现验证码，请求失败，Verifytype: {verify_type}，Verifyuuid: {verify_uuid}",
            response=response,
            verify_type=verify_type,
            verify_uuid=verify_uuid,
        )
    elif data.get("success"):
        return data.get("data", data.get("success"))
    elif data.get("code") == ErrorEnum.IP_BLOCK.value.code:
        raise IPBlockError(ErrorEnum.IP_BLOCK.value.msg)
    elif data.get("code") == ErrorEnum.SIGN_FAULT.value.code:
        raise SignError(ErrorEnum.SIGN_FAULT.value.msg)
    else:
        raise DataFetchError(data)


async def _xiaohongshu_sign(uri: str, cookies: str, data=None):
    sign_server_uri = "/signsrv/v1/xhs/sign"
    data = json.dumps({uri, data, cookies})
    res_json = await _request(method="POST", uri=sign_server_uri, json=data)
    if not res_json:
        raise Exception(f"从签名服务器获取签名失败")

    if res_json.isok:
        return res_json
    raise Exception(f"从签名服务器获取签名失败")


async def _pre_headers( uri: str, cookies: str, data=None) -> Dict:
    result = await _xiaohongshu_sign(uri, cookies, data)
    h = {
        "X-S": result.data.x_s,
        "X-T": result.data.x_t,
        "x-S-Common": result.data.x_s_common,
        "X-B3-Traceid": result.data.x_b3_traceid,
    }
    h.update(headers)
    return h


async def get(uri: str, params=None, **kwargs) -> Union[Response, Dict]:
    final_uri = uri
    if isinstance(params, dict):
        final_uri = f"{uri}?" f"{urlencode(params)}"
    try:
        headers = await _pre_headers(final_uri)
        res = await request(
            method="GET", url=f"{XHS_API_URL}{final_uri}", headers=headers, **kwargs
        )
        return res
    except RetryError as e:
        original_exception = e.last_attempt.exception()
        traceback.print_exception(
            type(original_exception),
            original_exception,
            original_exception.__traceback__,
        )

        utils.logger.error(
            f"get重试失败: {uri} 请尝试更换账号与IP再次发起重试"
        )
        await self.mark_account_invalid(self.account_info)
        await self.update_account_info()
        headers = await self._pre_headers(final_uri)
        return await self.request(
            method="GET", url=f"{XHS_API_URL}{final_uri}", headers=headers, **kwargs
        )
