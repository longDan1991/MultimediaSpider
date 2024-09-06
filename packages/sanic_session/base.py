import time
import datetime
import abc
import ujson
import uuid
from .utils import CallbackDict


def get_request_container(request):
    return request.ctx.__dict__ if hasattr(request, "ctx") else request


class SessionDict(CallbackDict):
    def __init__(self, initial=None, sid=None):
        def on_update(self):
            self.modified = True

        super().__init__(initial, on_update)

        self.sid = sid
        self.modified = False


class BaseSessionInterface(metaclass=abc.ABCMeta):
    # 此标志表示此接口是否需要请求/响应中间件钩子

    def __init__(
        self, expiry, prefix, cookie_name, domain, httponly, sessioncookie, samesite, session_name, secure,
    ):
        self.expiry = expiry
        self.prefix = prefix
        self.cookie_name = cookie_name
        self.domain = domain
        self.httponly = httponly
        self.sessioncookie = sessioncookie
        self.samesite = samesite
        self.session_name = session_name
        self.secure = secure

    def _delete_cookie(self, request, response):
        req = get_request_container(request)
        response.delete_cookie(self.cookie_name)

        # 我们设置expires/max-age，即使对于会话cookie也强制过期
        response.add_cookie(
            self.cookie_name,
            req[self.session_name].sid,
            expires=datetime.datetime.utcnow(),
            max_age=0
        )

    @staticmethod
    def _calculate_expires(expiry):
        expires = time.time() + expiry
        return datetime.datetime.fromtimestamp(expires)

    def _set_cookie_props(self, request, response):
        req = get_request_container(request)
        cookie_props = {
            "httponly": self.httponly,
            "samesite": self.samesite,
            "secure": self.secure
        }

        # 除非我们使用会话cookie，否则设置expires和max-age
        if not self.sessioncookie:
            cookie_props["expires"] = self._calculate_expires(self.expiry)
            cookie_props["max_age"] = self.expiry

        if self.domain:
            cookie_props["domain"] = self.domain

        response.add_cookie(
            self.cookie_name,
            req[self.session_name].sid,
            **cookie_props
        )

    @abc.abstractmethod
    async def _get_value(self, prefix: str, sid: str):
        """
        从数据存储中获取值。每个数据存储的具体实现。

        参数：
            prefix:
                键的前缀，用于命名空间键。
            sid:
                十六进制字符串形式的uuid
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def _delete_key(self, key: str):
        """从数据存储中删除键"""
        raise NotImplementedError

    @abc.abstractmethod
    async def _set_value(self, key: str, data: SessionDict):
        """为数据存储设置值"""
        raise NotImplementedError

    async def open(self, request) -> SessionDict:
        """
        在请求上打开一个会话。如果存在，则从数据存储中恢复客户端的会话。
        会话数据将在 `request.session` 上可用。

        参数：
            request (sanic.request.Request):
                将在其上打开会话的请求。

        返回：
            SessionDict:
                客户端的会话数据，
                同时附加到 `request.session`。
        """
        sid = request.cookies.get(self.cookie_name)

        if not sid:
            sid = uuid.uuid4().hex
            session_dict = SessionDict(sid=sid)
        else:
            val = await self._get_value(self.prefix, sid)
            if val is not None:
                data = ujson.loads(val)
                session_dict = SessionDict(data, sid=sid)
            else:
                session_dict = SessionDict(sid=sid)

        # 将会话数据附加到请求上，为方便起见返回它
        req = get_request_container(request)
        req[self.session_name] = session_dict

        return session_dict

    async def save(self, request, response) -> None:
        """将会话保存到数据存储。

        参数：
            request (sanic.request.Request):
                附加了会话的Sanic请求。
            response (sanic.response.Response):
                Sanic响应。具有适当过期时间的Cookie将被添加到此响应中。

        返回：
            None
        """
        req = get_request_container(request)
        if self.session_name not in req:
            return

        key = self.prefix + req[self.session_name].sid
        if not req[self.session_name]:
            await self._delete_key(key)

            if req[self.session_name].modified:
                self._delete_cookie(request, response)
            return

        val = ujson.dumps(dict(req[self.session_name]))
        await self._set_value(key, val)
        self._set_cookie_props(request, response)
