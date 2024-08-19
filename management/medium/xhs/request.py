from typing import Union, Dict
import json
from urllib.parse import urlencode
import httpx

from tenacity import RetryError, retry, stop_after_attempt, wait_fixed
from httpx import Response
from management.proxies.proxy import get_proxy
from tools import utils

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

header = {
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


async def _pre_headers(url: str, data=None) -> Dict:
    xhs_sign_resp = await _sign_client.sign(url, data, "")
    headers = {
        "X-S": xhs_sign_resp.data.x_s,
        "X-T": xhs_sign_resp.data.x_t,
        "x-S-Common": xhs_sign_resp.data.x_s_common,
        "X-B3-Traceid": xhs_sign_resp.data.x_b3_traceid,
    }
    headers.update(self.headers)
    return headers


async def get(uri: str, params=None, **kwargs) -> Union[Response, Dict]:
    final_uri = uri
    if isinstance(params, dict):
        final_uri = f"{uri}?" f"{urlencode(params)}"

    try:
        headers = await self._pre_headers(final_uri)
        res = await request(
            method="GET", url=f"{XHS_API_URL}{final_uri}", headers=headers, **kwargs
        )
        return res
    except RetryError:
        utils.logger.error(
            f"[XiaoHongShuClient.get] 重试了5次: {uri} 请求，均失败了，尝试更换账号与IP再次发起重试"
        )
        # 如果重试了5次次都还是异常了，那么尝试更换账号信息
        await self.mark_account_invalid(self.account_info)
        await self.update_account_info()
        headers = await self._pre_headers(final_uri)
        return await self.request(
            method="GET", url=f"{XHS_API_URL}{final_uri}", headers=headers, **kwargs
        )
