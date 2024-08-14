# -*- coding: utf-8 -*-
import asyncio
from typing import Any, Dict, Union

import aiohttp

import config
from pkg.rpc.sign_srv_client.sign_model import (DouyinSignRequest,
                                                DouyinSignResponse,
                                                XhsSignRequest,
                                                XhsSignResponse)
from pkg.tools import utils

SIGN_SERVER_URL = f"http://{config.SIGN_SRV_HOST}:{config.SIGN_SRV_PORT}"


class SignServerClient:
    def __init__(self, endpoint: str = SIGN_SERVER_URL, timeout: int = 60):
        """
        SignServerClient constructor
        Args:
            endpoint: sign server endpoint
            timeout: request timeout
        """
        self._endpoint = endpoint
        self._timeout = timeout

    async def request(self, method: str, uri: str, **kwargs) -> Union[Dict, Any]:
        """
        send request
        Args:
            method: request method
            uri: request uri
            **kwargs: other request params

        Returns:

        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout)) as session:
                async with session.request(method, self._endpoint + uri, **kwargs) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        utils.logger.error(
                            f"[XhsSignClient.request] response status code {response.status} response content: {response_text}")
                        raise Exception(f"请求签名服务器失败，状态码：{response.status}")

                    data = await response.json()
                    return data
        except Exception as e:
            raise Exception(f"请求签名服务器失败, error: {e}")

    async def xiaohongshu_sign(self, sign_req: XhsSignRequest) -> XhsSignResponse:
        """
        xiaohongshu sign request to sign server
        Args:
            sign_req:

        Returns:

        """
        sign_server_uri = "/signsrv/v1/xhs/sign"
        res_json = await self.request(method="POST", uri=sign_server_uri, json=sign_req.model_dump())
        if not res_json:
            raise Exception(f"从签名服务器:{SIGN_SERVER_URL}{sign_server_uri} 获取签名失败")

        xhs_sign_response = XhsSignResponse(**res_json)
        if xhs_sign_response.isok:
            return xhs_sign_response
        raise Exception(
            f"从签名服务器:{SIGN_SERVER_URL}{sign_server_uri} 获取签名失败，原因：{xhs_sign_response.msg}, sign reponse: {xhs_sign_response}")

    async def douyin_sign(self, sign_req: DouyinSignRequest) -> DouyinSignResponse:
        """
        douyin sign request to sign server
        Args:
            sign_req: DouyinSignRequest object

        Returns:

        """
        sign_server_uri = "/signsrv/v1/douyin/sign"
        res_json = await self.request(method="POST", uri=sign_server_uri, json=sign_req.model_dump())
        if not res_json:
            raise Exception(f"从签名服务器:{SIGN_SERVER_URL}{sign_server_uri} 获取签名失败")

        sign_response = DouyinSignResponse(**res_json)
        if sign_response.isok:
            return sign_response
        raise Exception(
            f"从签名服务器:{SIGN_SERVER_URL}{sign_server_uri} 获取签名失败，原因：{sign_response.msg}, sign reponse: {sign_response}")

    async def pong_sign_server(self):
        """
        test
        :return:
        """
        utils.logger.info("[XhsSignClient.pong_sign_server] test xhs sign server is alive")
        await self.request(method="GET", uri="/signsrv/pong")
        utils.logger.info("[XhsSignClient.pong_sign_server] xhs sign server is alive")


if __name__ == '__main__':
    sign_client = SignServerClient()
    asyncio.run(sign_client.pong_sign_server())
