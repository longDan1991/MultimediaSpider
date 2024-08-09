# -*- coding: utf-8 -*-
import json
from typing import Any, Dict, Optional, Union

import httpx

from constant.xiaohongshu import XHS_SIGN_SERVER_URL
from media_platform.xhs.exception import SignError
from model.m_xiaohongshu import XhsSignRequest, XhsSignResponse
from tools import utils


class XhsSignClient:
    def __init__(self, endpoint: str = XHS_SIGN_SERVER_URL, timeout: int = 60):
        """
        初始化XhsSignClient
        Args:
            endpoint:
            timeout:
        """
        self._endpoint = endpoint
        self._timeout = timeout

    async def request(self, method, url, **kwargs) -> Union[Dict, Any]:
        """
        发送请求
        Args:
            method:
            url:
            **kwargs:

        Returns:

        """
        try:
            async with httpx.AsyncClient(base_url=self._endpoint) as client:
                response = await client.request(
                    method, url, timeout=self._timeout,
                    **kwargs
                )
            data = response.json()
            return data
        except json.decoder.JSONDecodeError:
            return response.text

        except Exception as e:
            utils.logger.error(f"[XhsSignClient.request] request error: {e}")
            return None

    async def sign(self, uri: str, data: Optional[Dict] = None, cookies: str = None) -> Optional[XhsSignResponse]:
        """
        向签名服务器签名发起请求
        Args:
            uri: 请求签名的Uri
            data: post请求的body数据
            cookies: cookies

        Returns:

        """
        sign_server_uri = "/signsrv/v1/xhs/sign"
        xhs_sign_req = XhsSignRequest(
            uri=uri,
            data=data,
            cookies=cookies
        )
        post_data = {
            "uri": uri,
            "data": data,
            "cookies": cookies
        }
        res_json = await self.request(method="POST", url=sign_server_uri, json=post_data)
        if not res_json:
            raise SignError(f"从签名服务器:{XHS_SIGN_SERVER_URL}{sign_server_uri} 获取签名失败")

        xhs_sign_response = XhsSignResponse(**res_json)
        if xhs_sign_response.isok:
            return xhs_sign_response
        raise SignError(f"从签名服务器:{XHS_SIGN_SERVER_URL}{sign_server_uri} 获取签名失败，原因：{xhs_sign_response.msg}, sign reponse: {xhs_sign_response}")


    async def pong_sign_server(self):
        """
        test
        :return:
        """
        utils.logger.info("[XhsSignClient.pong_sign_server] test xhs sign server is alive")
        await self.request(method="GET", url="/signsrv/pong")
        utils.logger.info("[XhsSignClient.pong_sign_server] xhs sign server is alive")


