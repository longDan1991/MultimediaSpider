import asyncio
import json
import re
from typing import Callable, Dict, List, Optional, Union
from urllib.parse import urlencode, urlparse, parse_qs

import httpx
from httpx import Response
from tenacity import RetryError, retry, stop_after_attempt, wait_fixed

import config
from account_pool import AccountWithIpModel
from account_pool.pool import AccountWithIpPoolManager
from base.base_crawler import AbstractApiClient
from config import ENABLE_IP_PROXY
from constant.xiaohongshu import XHS_API_URL, XHS_INDEX_URL
from tools import utils

from .exception import (DataFetchError, ErrorEnum, IPBlockError,
                        NeedVerifyError, SignError)
from .field import SearchNoteType, SearchSortType
from .help import get_search_id
from .rpc.xhs_sign_client import XhsSignClient


class XiaoHongShuClient(AbstractApiClient):
    def __init__(
            self,
            timeout: int = 10,
            cookies: str = None,
            proxies: Dict = None,
            user_agent: str = None,
            account_with_ip_pool: AccountWithIpPoolManager = None
    ):
        """
        xhs client constructor
        Args:
            timeout: 请求超时时间配置
            cookies: 单个账号的cookies（不建议使用）
            proxies: 单个账号的代理（不建议使用）
            user_agent: 自定义的User-Agent
            account_with_ip_pool:
        """
        self.timeout = timeout
        self._cookies = cookies
        self._proxies = proxies
        self._user_agent = user_agent or utils.get_user_agent()
        self._sign_client = XhsSignClient()
        self._account_with_ip_pool = account_with_ip_pool
        self._current_account_with_ip: Optional[AccountWithIpModel] = None

    async def update_account_info(self):
        """
        更新客户端的账号信息，如果开启了IP代理，那么也会更新IP代理
        Returns:

        """
        if self._account_with_ip_pool:
            account_with_ip = await self._account_with_ip_pool.get_account_with_ip()
            self._cookies = account_with_ip.account.cookies
            if ENABLE_IP_PROXY:
                self._proxies = account_with_ip.ip.get_httpx_proxy()
            self._current_account_with_ip = account_with_ip

    async def mark_account_invalid(self, account_with_ip: AccountWithIpModel):
        """
        标记账号为无效
        Args:
            account_with_ip:

        Returns:

        """
        if self._account_with_ip_pool:
            await self._account_with_ip_pool.mark_account_invalid(account_with_ip.account)
            await self._account_with_ip_pool.mark_ip_invalid(account_with_ip.ip)

    async def _pre_headers(self, url: str, data=None) -> Dict:
        """
        请求头参数签名
        Args:
            url:
            data:

        Returns:

        """
        xhs_sign_resp = await self._sign_client.sign(url, data, self._cookies)
        headers = {
            "X-S": xhs_sign_resp.data.x_s,
            "X-T": xhs_sign_resp.data.x_t,
            "x-S-Common": xhs_sign_resp.data.x_s_common,
            "X-B3-Traceid": xhs_sign_resp.data.x_b3_traceid,
        }
        headers.update(self.headers)
        return headers

    @property
    def headers(self):
        return {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Cookie": self._cookies,
            "origin": "https://www.xiaohongshu.com",
            "referer": "https://www.xiaohongshu.com/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }

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
        need_return_ori_response = kwargs.get("return_response", False)
        if "return_response" in kwargs:
            del kwargs["return_response"]

        async with httpx.AsyncClient(proxies=self._proxies) as client:
            response = await client.request(
                method, url, timeout=self.timeout,
                **kwargs
            )

        if need_return_ori_response:
            return response

        try:
            data = response.json()
        except json.decoder.JSONDecodeError:
            return response

        if response.status_code == 471 or response.status_code == 461:
            # someday someone maybe will bypass captcha
            verify_type = response.headers['Verifytype']
            verify_uuid = response.headers['Verifyuuid']
            raise NeedVerifyError(
                f"出现验证码，请求失败，Verifytype: {verify_type}，Verifyuuid: {verify_uuid}",
                response=response, verify_type=verify_type, verify_uuid=verify_uuid)
        elif data.get("success"):
            return data.get("data", data.get("success"))
        elif data.get("code") == ErrorEnum.IP_BLOCK.value.code:
            raise IPBlockError(ErrorEnum.IP_BLOCK.value.msg, response=response)
        elif data.get("code") == ErrorEnum.SIGN_FAULT.value.code:
            raise SignError(ErrorEnum.SIGN_FAULT.value.msg, response=response)
        else:
            raise DataFetchError(data, response=response)

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
            headers = await self._pre_headers(final_uri)
            res = await self.request(method="GET", url=f"{XHS_API_URL}{final_uri}", headers=headers, **kwargs)
            return res
        except RetryError:
            utils.logger.error(f"[XiaoHongShuClient.post] 重试了5次:{uri} 请求，均失败了，尝试更换账号与IP再次发起重试")
            # 如果重试了5次次都还是异常了，那么尝试更换账号信息
            await self.mark_account_invalid(self._current_account_with_ip)
            await self.update_account_info()
            headers = await self._pre_headers(final_uri)
            return await self.request(method="GET", url=f"{XHS_API_URL}{final_uri}", headers=headers, **kwargs)

    async def post(self, uri: str, data: dict, **kwargs) -> Union[Dict, Response]:
        """
        POST请求，对请求头签名
        Args:
            uri: 请求路由
            data: 请求体参数

        Returns:

        """
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        try:
            headers = await self._pre_headers(uri, data)
            res = await self.request(method="POST", url=f"{XHS_API_URL}{uri}",
                                     data=json_str, headers=headers, **kwargs)
            return res
        except RetryError:
            utils.logger.error(f"[XiaoHongShuClient.post] 重试了5次:{uri} 请求，均失败了，尝试更换账号与IP再次发起重试")
            # 如果重试了5次次都还是异常了，那么尝试更换账号信息
            await self.mark_account_invalid(self._current_account_with_ip)
            await self.update_account_info()
            headers = await self._pre_headers(uri, data)
            return await self.request(method="POST", url=f"{XHS_API_URL}{uri}",
                                      data=json_str, headers=headers, **kwargs)

    async def pong(self) -> bool:
        """
        用于检查登录态和签名服务是否失效了
        Returns:

        """
        await self._sign_client.pong_sign_server()
        utils.logger.info("[XiaoHongShuClient.pong] Begin to check login state...")
        ping_flag = False
        try:
            note_card: Dict = await self.get_note_by_keyword(keyword="小红书")
            if note_card.get("items"):
                ping_flag = True
        except Exception as e:
            utils.logger.error(f"[XiaoHongShuClient.pong] Ping xhs failed: {e}, and try to login again...")
            ping_flag = False
        utils.logger.info(f"[XiaoHongShuClient.pong] Login state result: {ping_flag}")
        return ping_flag

    async def get_note_by_keyword(
            self, keyword: str,
            page: int = 1, page_size: int = 20,
            sort: SearchSortType = SearchSortType.GENERAL,
            note_type: SearchNoteType = SearchNoteType.ALL
    ) -> Dict:
        """
        根据关键词搜索笔记
        Args:
            keyword: 关键词参数
            page: 分页第几页
            page_size: 分页数据长度
            sort: 搜索结果排序指定
            note_type: 搜索的笔记类型

        Returns:

        """
        uri = "/api/sns/web/v1/search/notes"
        data = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": get_search_id(),
            "sort": sort.value,
            "note_type": note_type.value
        }
        return await self.post(uri, data)

    async def get_note_by_id(self, note_id: str, xsec_source: str, xsec_token: str) -> Dict:
        """
        获取笔记详情API
        Args:
            note_id:笔记ID
            xsec_source: 渠道来源
            xsec_token: 搜索关键字之后返回的比较列表中返回的token

        Returns:

        """
        if not xsec_source:
            xsec_source = "pc_search"

        data = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1},
            "xsec_source": xsec_source,
            "xsec_token": xsec_token
        }
        uri = "/api/sns/web/v1/feed"
        res = await self.post(uri, data)
        if res and res.get("items"):
            res_dict: Dict = res["items"][0]["note_card"]
            return res_dict
        # 爬取频繁了可能会出现有的笔记能有结果有的没有
        utils.logger.error(f"[XiaoHongShuClient.get_note_by_id] get note id:{note_id} empty and res:{res}")
        return dict()

    async def get_note_comments(self, note_id: str, cursor: str = "") -> Dict:
        """
        获取一级评论的API
        Args:
            note_id: 笔记ID
            cursor: 分页游标

        Returns:

        """
        uri = "/api/sns/web/v2/comment/page"
        params = {
            "note_id": note_id,
            "cursor": cursor,
            "top_comment_id": "",
            "image_formats": "jpg,webp,avif"
        }
        return await self.get(uri, params)

    async def get_note_sub_comments(self, note_id: str, root_comment_id: str, num: int = 10, cursor: str = ""):
        """
        获取指定父评论下的子评论的API
        Args:
            note_id: 子评论的帖子ID
            root_comment_id: 根评论ID
            num: 分页数量
            cursor: 分页游标

        Returns:

        """
        uri = "/api/sns/web/v2/comment/sub/page"
        params = {
            "note_id": note_id,
            "root_comment_id": root_comment_id,
            "num": num,
            "cursor": cursor,
        }
        return await self.get(uri, params)

    async def get_note_all_comments(self, note_id: str, crawl_interval: float = 1.0,
                                    callback: Optional[Callable] = None) -> List[Dict]:
        """
        获取指定笔记下的所有一级评论，该方法会一直查找一个帖子下的所有评论信息
        Args:
            note_id: 笔记ID
            crawl_interval: 爬取一次笔记的延迟单位（秒）
            callback: 一次笔记爬取结束后

        Returns:

        """
        result = []
        comments_has_more = True
        comments_cursor = ""
        while comments_has_more:
            comments_res = await self.get_note_comments(note_id, comments_cursor)
            comments_has_more = comments_res.get("has_more", False)
            comments_cursor = comments_res.get("cursor", "")
            if "comments" not in comments_res:
                utils.logger.info(
                    f"[XiaoHongShuClient.get_note_all_comments] No 'comments' key found in response: {comments_res}")
                break
            comments = comments_res["comments"]
            if callback:
                await callback(note_id, comments)
            await asyncio.sleep(crawl_interval)
            result.extend(comments)
            sub_comments = await self.get_comments_all_sub_comments(comments, crawl_interval, callback)
            result.extend(sub_comments)
        return result

    async def get_comments_all_sub_comments(self, comments: List[Dict], crawl_interval: float = 1.0,
                                            callback: Optional[Callable] = None) -> List[Dict]:
        """
        获取指定一级评论下的所有二级评论, 该方法会一直查找一级评论下的所有二级评论信息
        Args:
            comments: 评论列表
            crawl_interval: 爬取一次评论的延迟单位（秒）
            callback: 一次评论爬取结束后

        Returns:

        """
        if not config.ENABLE_GET_SUB_COMMENTS:
            utils.logger.info(
                f"[XiaoHongShuCrawler.get_comments_all_sub_comments] Crawling sub_comment mode is not enabled")
            return []

        result = []
        for comment in comments:
            note_id = comment.get("note_id")
            sub_comments = comment.get("sub_comments")
            if sub_comments and callback:
                await callback(note_id, sub_comments)

            sub_comment_has_more = comment.get("sub_comment_has_more")
            if not sub_comment_has_more:
                continue

            root_comment_id = comment.get("id")
            sub_comment_cursor = comment.get("sub_comment_cursor")

            while sub_comment_has_more:
                comments_res = await self.get_note_sub_comments(note_id, root_comment_id, 10, sub_comment_cursor)
                sub_comment_has_more = comments_res.get("has_more", False)
                sub_comment_cursor = comments_res.get("cursor", "")
                if "comments" not in comments_res:
                    utils.logger.info(
                        f"[XiaoHongShuClient.get_comments_all_sub_comments] No 'comments' key found in response: {comments_res}")
                    break
                comments = comments_res["comments"]
                if callback:
                    await callback(note_id, comments)
                await asyncio.sleep(crawl_interval)
                result.extend(comments)
        return result

    async def get_creator_info(self, user_id: str) -> Dict:
        """
        通过解析网页版的用户主页HTML，获取用户个人简要信息
        PC端用户主页的网页存在window.__INITIAL_STATE__这个变量上的，解析它即可
        eg: https://www.xiaohongshu.com/user/profile/59d8cb33de5fb4696bf17217
        """
        uri = f"/user/profile/{user_id}"
        response: Response = await self.request("GET", XHS_INDEX_URL + uri, return_response=True)
        match = re.search(r'<script>window.__INITIAL_STATE__=(.+)<\/script>', response.text, re.M)

        if match is None:
            return {}

        info = json.loads(match.group(1).replace(':undefined', ':null'), strict=False)
        if info is None:
            return {}
        return info.get('user').get('userPageData')

    async def get_notes_by_creator(
            self, creator: str,
            cursor: str,
            page_size: int = 30
    ) -> Dict:
        """
        获取博主的笔记
        Args:
            creator: 博主ID
            cursor: 上一页最后一条笔记的ID
            page_size: 分页数据长度

        Returns:

        """
        uri = "/api/sns/web/v1/user_posted"
        data = {
            "user_id": creator,
            "cursor": cursor,
            "num": page_size,
            "image_formats": "jpg,webp,avif"
        }
        return await self.get(uri, data)

    async def get_all_notes_by_creator(self, user_id: str, crawl_interval: float = 1.0,
                                       callback: Optional[Callable] = None) -> List[Dict]:
        """
        获取指定用户下的所有发过的帖子，该方法会一直查找一个用户下的所有帖子信息
        Args:
            user_id: 用户ID
            crawl_interval: 爬取一次的延迟单位（秒）
            callback: 一次分页爬取结束后的更新回调函数

        Returns:

        """
        result = []
        notes_has_more = True
        notes_cursor = ""
        while notes_has_more:
            notes_res = await self.get_notes_by_creator(user_id, notes_cursor)
            if not notes_res:
                utils.logger.error(
                    f"[XiaoHongShuClient.get_notes_by_creator] The current creator may have been banned by xhs, so they cannot access the data.")
                break

            notes_has_more = notes_res.get("has_more", False)
            notes_cursor = notes_res.get("cursor", "")
            if "notes" not in notes_res:
                utils.logger.info(
                    f"[XiaoHongShuClient.get_all_notes_by_creator] No 'notes' key found in response: {notes_res}")
                break

            notes = notes_res["notes"]
            utils.logger.info(
                f"[XiaoHongShuClient.get_all_notes_by_creator] got user_id:{user_id} notes len : {len(notes)}")
            if callback:
                await callback(notes)
            await asyncio.sleep(crawl_interval)
            result.extend(notes)
        return result

    async def get_note_by_id_from_html(self, note_id: str):
        """
        通过解析网页版的笔记详情页HTML，获取笔记详情
        Args:
            note_id:

        Returns:

        """
        def camel_to_underscore(key):
            return re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()

        def transform_json_keys(json_data):
            data_dict = json.loads(json_data)
            dict_new = {}
            for key, value in data_dict.items():
                new_key = camel_to_underscore(key)
                if not value:
                    dict_new[new_key] = value
                elif isinstance(value, dict):
                    dict_new[new_key] = transform_json_keys(json.dumps(value))
                elif isinstance(value, list):
                    dict_new[new_key] = [
                        transform_json_keys(json.dumps(item))
                        if (item and isinstance(item, dict))
                        else item
                        for item in value
                    ]
                else:
                    dict_new[new_key] = value
            return dict_new

        url = "https://www.xiaohongshu.com/explore/" + note_id
        res = await self.request(method="GET", url=url, return_response=True, headers=self.headers)
        html = res.text
        state = re.findall(r"window.__INITIAL_STATE__=({.*})</script>", html)[0].replace("undefined", '""')
        if state != "{}":
            note_dict = transform_json_keys(state)
            return note_dict["note"]["note_detail_map"][note_id]["note"]
        elif ErrorEnum.IP_BLOCK.value in html:
            raise IPBlockError(ErrorEnum.IP_BLOCK.value)
        raise DataFetchError(html)

    async def get_note_short_url(self, note_id: str) -> Dict:
        """
        获取笔记的短链接
        Args:
            note_id: 笔记ID

        Returns:

        """
        uri = f"/api/sns/web/short_url"
        data = {
            "original_url": f"{XHS_INDEX_URL}/discovery/item/{note_id}?a=1"
        }
        response: Response = await self.post(uri, data=data, return_response=True)
        return response.json()
