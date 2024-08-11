# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/23 15:40
# @Desc    : 微博爬虫 API 请求 client

import asyncio
import copy
import json
import re
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from httpx import Response
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

import config
from account_pool import AccountWithIpModel
from account_pool.pool import AccountWithIpPoolManager
from constant.weibo import WEIBO_API_URL
from tools import utils

from .exception import DataFetchError
from .field import SearchType


class WeiboClient:
    def __init__(
            self,
            timeout: int = 10,
            user_agent: str = None,
            account_with_ip_pool: AccountWithIpPoolManager = None
    ):
        """
        weibo client constructor
        Args:
            timeout: 请求超时时间
            user_agent: 请求头中的 User-Agent
            account_with_ip_pool: 账号池管理器
        """
        self.timeout = timeout
        self._user_agent = user_agent or utils.get_user_agent()
        self._account_with_ip_pool = account_with_ip_pool
        self.account_info: Optional[AccountWithIpModel] = None

    @property
    def headers(self):
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Cookie": self._cookies,
            "origin": "https://m.weibo.cn/",
            "referer": "https://m.weibo.cn/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }

    @property
    def _proxies(self):
        return self.account_info.ip_info.format_httpx_proxy() if self.account_info.ip_info else None

    @property
    def _cookies(self):
        return self.account_info.account.cookies

    async def update_account_info(self):
        """
        更新客户端的账号信息
        Returns:

        """
        self.account_info = await self._account_with_ip_pool.get_account_with_ip_info()

    async def mark_account_invalid(self, account_with_ip: AccountWithIpModel):
        """
        标记账号为无效
        Args:
            account_with_ip:

        Returns:

        """
        if self._account_with_ip_pool:
            await self._account_with_ip_pool.mark_account_invalid(account_with_ip.account)
            await self._account_with_ip_pool.mark_ip_invalid(account_with_ip.ip_info)

    async def check_ip_expired(self):
        """
        检查IP是否过期, 由于IP的过期时间在运行中是不确定的，所以每次请求都需要验证下IP是否过期
        如果过期了，那么需要重新获取一个新的IP，赋值给当前账号信息
        Returns:

        """
        if config.ENABLE_IP_PROXY and self.account_info.ip_info and self.account_info.ip_info.is_expired:
            utils.logger.info(
                f"[XiaoHongShuClient.request] current ip {self.account_info.ip_info.ip} is expired, "
                f"mark it invalid and try to get a new one")
            await self._account_with_ip_pool.mark_ip_invalid(self.account_info.ip_info)
            self.account_info.ip_info = await self._account_with_ip_pool.proxy_ip_pool.get_proxy()

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
    async def request(self, method, url, **kwargs) -> Union[Response, Dict]:
        """
        封装httpx的公共请求方法，对请求响应做一些处理
        Args:
            method: 请求方法
            url: 请求的URL
            **kwargs: 其他请求参数，例如请求头、请求体等

        Returns:

        """
        await self.check_ip_expired()
        need_return_ori_response = kwargs.get("return_response", False)
        if "return_response" in kwargs:
            del kwargs["return_response"]
        headers = kwargs.pop("headers", None) or self.headers
        async with httpx.AsyncClient(proxies=self._proxies) as client:
            response = await client.request(
                method, url, timeout=self.timeout, headers=headers,
                **kwargs
            )

        if need_return_ori_response:
            return response

        data: Dict = response.json()
        if data.get("ok") not in [1, 0]:
            # 0和1是正常的返回码，其他的都是异常，0代表无数据，1代表有数据
            utils.logger.error(f"[WeiboClient.request] request {method}:{url} err, res:{data}")
            raise DataFetchError(data.get("msg", "unkonw error"))
        else:
            return data.get("data", {})

    async def get(self, uri: str, params=None, **kwargs) -> Union[Response, Dict]:
        """
        GET请求，对请求头签名
        Args:
            uri: 请求路由
            params: 请求参数

        Returns:

        """
        final_uri = uri
        if isinstance(params, dict):
            final_uri = (f"{uri}?"
                         f"{urlencode(params)}")

        try:
            res = await self.request(method="GET", url=f"{WEIBO_API_URL}{final_uri}", **kwargs)
            return res
        except RetryError:
            utils.logger.error(f"[WeiboClient.get] 请求uri:{uri} 重试均失败了，尝试更换账号与IP再次发起重试")
            try:
                utils.logger.info(f"[WeiboClient.get] 请求uri:{uri} 尝试更换IP再次发起重试...")
                await self._account_with_ip_pool.mark_ip_invalid(self.account_info.ip_info)
                self.account_info.ip_info = await self._account_with_ip_pool.proxy_ip_pool.get_proxy()
                return await self.request(method="GET", url=f"{WEIBO_API_URL}{final_uri}", **kwargs)

            except RetryError:
                utils.logger.error(
                    f"[WeiboClient.get]请求uri:{uri}，IP更换后还是失败，尝试更换账号与IP再次发起重试")
                await self.mark_account_invalid(self.account_info)
                await self.update_account_info()
                return await self.request(method="GET", url=f"{WEIBO_API_URL}{final_uri}", **kwargs)

    async def post(self, uri: str, data: Dict, **kwargs) -> Union[Response, Dict]:
        """
        POST请求，对请求头签名
        Args:
            uri: 请求路由
            data: 请求体参数

        Returns:

        """
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        try:
            res = await self.request(method="POST", url=f"{WEIBO_API_URL}{uri}",
                                     data=json_str, **kwargs)
            return res
        except RetryError:
            utils.logger.error(f"[WeiboClient.post] 请求uri:{uri} 重试均失败了，尝试更换账号与IP再次发起重试")
            try:
                utils.logger.info(f"[WeiboClient.post] 请求uri:{uri} 尝试更换IP再次发起重试...")
                await self._account_with_ip_pool.mark_ip_invalid(self.account_info.ip_info)
                self.account_info.ip_info = await self._account_with_ip_pool.proxy_ip_pool.get_proxy()
                res = await self.request(method="POST", url=f"{WEIBO_API_URL}{uri}",
                                         data=json_str, **kwargs)

                return res
            except RetryError:
                utils.logger.error(
                    f"[WeiboClient.post]请求uri:{uri}，IP更换后还是失败，尝试更换账号与IP再次发起重试")
                await self.mark_account_invalid(self.account_info)
                await self.update_account_info()
                res = await self.request(method="POST", url=f"{WEIBO_API_URL}{uri}",
                                         data=json_str, **kwargs)

                return res

    async def pong(self) -> bool:
        """get a note to check if login state is ok"""
        utils.logger.info("[WeiboClient.pong] Begin pong weibo...")
        ping_flag = False
        try:
            uri = "/api/config"
            resp_data: Dict = await self.request(method="GET", url=f"{WEIBO_API_URL}{uri}")
            if resp_data.get("login"):
                ping_flag = True
            else:
                utils.logger.error(f"[WeiboClient.pong] cookie may be invalid and again login...")
        except Exception as e:
            utils.logger.error(f"[WeiboClient.pong] Pong weibo failed: {e}, and try to login again...")
            ping_flag = False
        return ping_flag

    async def get_note_by_keyword(
            self,
            keyword: str,
            page: int = 1,
            search_type: SearchType = SearchType.DEFAULT
    ) -> Dict:
        """
        search note by keyword
        :param keyword: 微博搜搜的关键词
        :param page: 分页参数 -当前页码
        :param search_type: 搜索的类型，见 weibo/filed.py 中的枚举SearchType
        :return:
        """
        uri = "/api/container/getIndex"
        containerid = f"100103type={search_type.value}&q={keyword}"
        params = {
            "containerid": containerid,
            "page_type": "searchall",
            "page": page,
        }
        return await self.get(uri, params)

    async def get_note_comments(self, mid_id: str, max_id: int) -> Dict:
        """get notes comments
        :param mid_id: 微博ID
        :param max_id: 分页参数ID
        :return:
        """
        uri = "/comments/hotflow"
        params = {
            "id": mid_id,
            "mid": mid_id,
            "max_id_type": 0,
        }
        if max_id > 0:
            params.update({"max_id": max_id})

        referer_url = f"https://m.weibo.cn/detail/{mid_id}"
        headers = copy.copy(self.headers)
        headers["Referer"] = referer_url

        return await self.get(uri, params, headers=headers)

    async def get_note_all_comments(self, note_id: str, crawl_interval: float = 1.0,
                                    callback: Optional[Callable] = None, ):
        """
        get note all comments include sub comments
        :param note_id:
        :param crawl_interval:
        :param callback:
        :return:
        """

        result = []
        is_end = False
        max_id = -1
        while not is_end:
            comments_res = await self.get_note_comments(note_id, max_id)
            if not comments_res:
                break
            max_id: int = comments_res.get("max_id")
            comment_list: List[Dict] = comments_res.get("data", [])
            is_end = max_id == 0
            if callback:  # 如果有回调函数，就执行回调函数
                await callback(note_id, comment_list)
            await asyncio.sleep(crawl_interval)
            result.extend(comment_list)
            sub_comment_result = await self.get_comments_all_sub_comments(note_id, comment_list, callback)
            result.extend(sub_comment_result)
        return result

    @staticmethod
    async def get_comments_all_sub_comments(note_id: str, comment_list: List[Dict],
                                            callback: Optional[Callable] = None) -> List[Dict]:
        """
        获取评论的所有子评论
        Args:
            note_id:
            comment_list:
            callback:

        Returns:

        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            utils.logger.info(
                f"[WeiboClient.get_comments_all_sub_comments] Crawling sub_comment mode is not enabled")
            return []

        res_sub_comments = []
        for comment in comment_list:
            sub_comments = comment.get("comments")
            if sub_comments and isinstance(sub_comments, list):
                await callback(note_id, sub_comments)
                res_sub_comments.extend(sub_comments)
        return res_sub_comments

    async def get_note_info_by_id(self, note_id: str) -> Dict:
        """
        根据帖子ID获取详情
        :param note_id:
        :return:
        """
        uri = f"/detail/{note_id}"
        response: Response = await self.get(uri, return_response=True)
        if response.status_code != 200:
            raise DataFetchError(f"get weibo detail err: {response.text}")
        match = re.search(r'var \$render_data = (\[.*?\])\[0\]', response.text, re.DOTALL)
        if match:
            render_data_json = match.group(1)
            render_data_dict = json.loads(render_data_json)
            note_detail = render_data_dict[0].get("status")
            note_item = {
                "mblog": note_detail
            }
            return note_item
        else:
            utils.logger.info(f"[WeiboClient.get_note_info_by_id] 未找到$render_data的值")
            return dict()
