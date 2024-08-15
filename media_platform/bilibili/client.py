# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2023/12/2 18:44
# @Desc    : bilibili 请求客户端
import asyncio
import json
import traceback
from typing import Callable, Dict, List, Optional, Union
from urllib.parse import urlencode

import httpx
from httpx import Response
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

import config
from base.base_crawler import AbstractApiClient
from constant.bilibili import BILI_API_URL, BILI_INDEX_URL
from pkg.account_pool import AccountWithIpModel
from pkg.account_pool.pool import AccountWithIpPoolManager
from pkg.rpc.sign_srv_client import BilibliSignRequest, SignServerClient
from pkg.tools import utils

from .exception import DataFetchError
from .field import CommentOrderType, SearchOrderType


class BilibiliClient(AbstractApiClient):
    def __init__(
            self,
            timeout: int = 10,
            user_agent: str = None,
            account_with_ip_pool: AccountWithIpPoolManager = None
    ):
        """
        bilibili client constructor
        Args:
            timeout: 请求超时时间配置
            user_agent: 自定义的User-Agent
            account_with_ip_pool: 账号池管理器
        """
        self.timeout = timeout
        self._user_agent = user_agent or utils.get_user_agent()
        self._sign_client = SignServerClient()
        self.account_with_ip_pool = account_with_ip_pool
        self.account_info: Optional[AccountWithIpModel] = None

    @property
    def headers(self):
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Cookie": self._cookies,
            "origin": BILI_INDEX_URL,
            "referer": BILI_INDEX_URL,
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
        self.account_info = await self.account_with_ip_pool.get_account_with_ip_info()

    async def mark_account_invalid(self, account_with_ip: AccountWithIpModel):
        """
        标记账号为无效
        Args:
            account_with_ip:

        Returns:

        """
        if self.account_with_ip_pool:
            await self.account_with_ip_pool.mark_account_invalid(account_with_ip.account)
            await self.account_with_ip_pool.mark_ip_invalid(account_with_ip.ip_info)

    async def pre_request_data(self, req_data: Dict) -> Dict:
        """
        发送请求进行请求参数签名
        :param req_data:
        :return:
        """
        if not req_data:
            return {}
        sign_req = BilibliSignRequest(
            req_data=req_data,
            cookies=self._cookies
        )
        sign_resp = await self._sign_client.bilibili_sign(sign_req)
        req_data.update({"wts": sign_resp.data.wts, "w_rid": sign_resp.data.w_rid})
        return req_data

    async def check_ip_expired(self):
        """
        检查IP是否过期, 由于IP的过期时间在运行中是不确定的，所以每次请求都需要验证下IP是否过期
        如果过期了，那么需要重新获取一个新的IP，赋值给当前账号信息
        Returns:

        """
        if config.ENABLE_IP_PROXY and self.account_info.ip_info and self.account_info.ip_info.is_expired:
            utils.logger.info(
                f"[BilibiliClient.request] current ip {self.account_info.ip_info.ip} is expired, "
                f"mark it invalid and try to get a new one")
            await self.account_with_ip_pool.mark_ip_invalid(self.account_info.ip_info)
            self.account_info.ip_info = await self.account_with_ip_pool.proxy_ip_pool.get_proxy()

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
        async with httpx.AsyncClient(proxies=self._proxies) as client:
            response = await client.request(
                method, url, timeout=self.timeout,
                **kwargs
            )
        try:
            data: Dict = response.json()
            if data.get("code") != 0:
                if data.get("code") == -404: # 这种情况多半是请求的资源不可见了（被隐藏了或者被删除了）
                    utils.logger.warn(f"[BilibiliClient.request] 请求失败: {url}, error: {data.get('message')}")
                    return {}
                raise DataFetchError(data.get("message", "unkonw error"))
            else:
                return data.get("data", {})
        except Exception as e:
            utils.logger.error(f"[BilibiliClient.request] 请求失败: {url}, error: {e}, response: {response.text}")
            raise DataFetchError("数据请求失败")

    async def get(self, uri: str, params=None, enable_params_sign: bool = True, **kwargs) -> Union[Dict, Response]:
        """
        GET请求，对请求头参数进行签名
        Args:
            uri: 请求路径
            params: 请求参数
            enable_params_sign: 是否对请求参数进行签名

        Returns:

        """
        final_uri = uri
        try:
            if enable_params_sign:
                params = await self.pre_request_data(params)
            if isinstance(params, dict):
                final_uri = (f"{uri}?"
                             f"{urlencode(params)}")
            return await self.request(method="GET", url=f"{BILI_API_URL}{final_uri}", headers=self.headers, **kwargs)
        except RetryError as e:
            # 获取原始异常
            original_exception = e.last_attempt.exception()
            traceback.print_exception(type(original_exception), original_exception, original_exception.__traceback__)

            utils.logger.error(f"[BilibiliClient.get] 重试了5次: {uri} 请求，均失败了，尝试更换账号与IP再次发起重试, error: {e}")
            await self.mark_account_invalid(self.account_info)
            await self.update_account_info()
            if enable_params_sign:
                params = await self.pre_request_data(params)
            if isinstance(params, dict):
                final_uri = (f"{uri}?"
                             f"{urlencode(params)}")
            return await self.request(method="GET", url=f"{BILI_API_URL}{final_uri}", headers=self.headers, **kwargs)

    async def post(self, uri: str, data: dict) -> Union[Dict, Response]:
        """
        POST请求, 对请求参数进行签名
        Args:
            uri: 请求路径
            data: 请求参数

        Returns:

        """
        try:
            data = await self.pre_request_data(data)
            json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            return await self.request(method="POST", url=f"{BILI_API_URL}{uri}",
                                      data=json_str, headers=self.headers)
        except RetryError as e:
            # 获取原始异常
            original_exception = e.last_attempt.exception()
            traceback.print_exception(type(original_exception), original_exception, original_exception.__traceback__)

            utils.logger.error(f"[BilibiliClient.post] 重试了5次: {uri} 请求，均失败了，尝试更换账号与IP再次发起重试")
            await self.mark_account_invalid(self.account_info)
            await self.update_account_info()
            data = await self.pre_request_data(data)
            json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            return await self.request(method="POST", url=f"{BILI_API_URL}{uri}",
                                      data=json_str, headers=self.headers)

    async def pong(self) -> bool:
        """
        ping bilibili to check login state
        Returns:

        """
        utils.logger.info("[BilibiliClient.pong] Begin pong bilibili...")
        ping_flag = False
        try:
            check_login_uri = "/x/web-interface/nav"
            response = await self.get(check_login_uri)
            if response.get("isLogin"):
                ping_flag = True
        except Exception as e:
            utils.logger.error(
                f"[BilibiliClient.pong] Pong bilibili failed: {e}")
            ping_flag = False
        return ping_flag

    async def search_video_by_keyword(self, keyword: str, page: int = 1, page_size: int = 20,
                                      order: SearchOrderType = SearchOrderType.DEFAULT):
        """
        search video by keyword
        Args:
            keyword: 搜索关键词
            page: 分页参数具体第几页
            page_size: 每一页参数的数量
            order: 搜索结果排序，默认位综合排序

        Returns:

        """
        uri = "/x/web-interface/wbi/search/type"
        post_data = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "order": order.value
        }
        return await self.get(uri, post_data)

    async def get_video_info(self, aid: Optional[int] = None, bvid: Optional[str] = None) -> Dict:
        """
        Bilibli web video detail api, aid 和 bvid任选一个参数
        Args:
            aid: 稿件avid
            bvid: 稿件bvid

        Returns:

        """
        if not aid and not bvid:
            raise ValueError("请提供 aid 或 bvid 中的至少一个参数")

        uri = "/x/web-interface/view/detail"
        params = dict()
        if aid:
            params.update({"aid": aid})
        else:
            params.update({"bvid": bvid})
        return await self.get(uri, params, enable_params_sign=True)

    async def get_video_comments(self, video_id: str, order_mode: CommentOrderType = CommentOrderType.DEFAULT,
                                 next_page: int = 0) -> Dict:
        """
        获取视频评论
        Args:
            video_id: 视频 ID
            order_mode: 排序方式
            next_page: 评论页选择

        Returns:

        """
        uri = "/x/v2/reply/wbi/main"
        post_data = {
            "oid": video_id,
            "mode": order_mode.value,
            "type": 1,
            "ps": 20,
            "next": next_page
        }
        return await self.get(uri, post_data)

    async def get_video_sub_comments(self, video_id: str, root_comment_id: str, pn: int, ps: int,
                                     order_mode: CommentOrderType):
        """
        获取
        Args:
            video_id: 子评论的视频ID
            root_comment_id: 根评论ID
            pn:
            ps:
            order_mode: 排序方式

        Returns:

        """
        uri = "/x/v2/reply/reply"
        params = {
            "oid": video_id,
            "mode": order_mode.value,
            "type": 1,
            "ps": ps,
            "pn": pn,
            "root": root_comment_id,
        }
        return await self.get(uri, params)

    async def get_video_all_comments(self, video_id: str, crawl_interval: float = 1.0,
                                     callback: Optional[Callable] = None):
        """
        获取视频所有评论
        Args:
            video_id: 视频ID
            crawl_interval: 爬取间隔
            callback:

        Returns:

        """

        result = []
        is_end = False
        next_page = 0
        while not is_end:
            comments_res = await self.get_video_comments(video_id, CommentOrderType.DEFAULT, next_page)
            cursor_info: Dict = comments_res.get("cursor")
            comment_list: List[Dict] = comments_res.get("replies", [])
            is_end = cursor_info.get("is_end")
            next_page = cursor_info.get("next")
            if callback:
                await callback(video_id, comment_list)
            await asyncio.sleep(crawl_interval)
            result.extend(comment_list)
            sub_comments = await self.get_comments_all_sub_comments(video_id, comment_list, crawl_interval, callback)
            result.extend(sub_comments)
        return result

    async def get_comments_all_sub_comments(self, video_id: str, comments: List[Dict], crawl_interval: float = 1.0,
                                            callback: Optional[Callable] = None) -> List[Dict]:
        """
        获取指定一级评论下的所有二级评论, 该方法会一直查找一级评论下的所有二级评论信息
        Args:
            video_id: 视频ID
            comments: 评论列表
            crawl_interval: 爬取一次评论的延迟单位（秒）
            callback: 一次评论爬取结束后

        Returns:

        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            return []

        if not comments:
            return []

        result = []
        for comment in comments:
            if comment.get("rcount", 0) == 0:
                continue
            sub_comment_has_more = True
            rpid = comment.get("rpid")
            page_num = 1
            page_size = 10
            while sub_comment_has_more:
                sub_comments_res = await self.get_video_sub_comments(
                    video_id=video_id,
                    root_comment_id=rpid,
                    pn=page_num,
                    ps=page_size,
                    order_mode=CommentOrderType.DEFAULT
                )
                sub_comments = sub_comments_res.get("replies", [])
                if callback:
                    await callback(video_id, sub_comments)
                await asyncio.sleep(crawl_interval)
                result.extend(sub_comments)
                sub_comment_has_more = sub_comments_res.get("page").get("count") > page_num * page_size
                page_num += 1

        return result

    async def get_creator_videos(self, creator_id: str, page_num: int, page_size: int = 30,
                                 order_mode: SearchOrderType = SearchOrderType.LAST_PUBLISH) -> Dict:
        """
        获取创作者的视频列表
        Args:
            creator_id: 创作者 ID
            page_num:
            page_size:
            order_mode:

        Returns:

        """
        uri = "/x/space/wbi/arc/search"
        post_data = {
            "mid": creator_id,
            "pn": page_num,
            "ps": page_size,
            "order": order_mode.value,
        }
        return await self.get(uri, post_data)

    async def get_all_videos_by_creator(self, creator_id: str,
                                        order_mode: SearchOrderType = SearchOrderType.LAST_PUBLISH) -> List[Dict]:
        """
        获取创作者的所有视频
        Args:
            creator_id: 创作者 ID
            order_mode: 排序方式

        Returns:

        """
        result = []
        page_num = 1
        page_size = 30
        has_more = True
        while has_more:
            videos_res = await self.get_creator_videos(creator_id, page_num, page_size, order_mode)
            video_list = videos_res.get("list", {}).get("vlist", [])
            result.extend(video_list)
            has_more = videos_res.get("page").get("count") > page_num * page_size
            page_num += 1
        return result
