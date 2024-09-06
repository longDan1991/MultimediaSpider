from datetime import datetime, timedelta
import warnings
from .base import BaseSessionInterface
from tortoise.expressions import Q
from models.sessions import Sessions
import ujson

class TortoiseSessionInterface(BaseSessionInterface):
    def __init__(
        self,
        domain: str = None,
        expiry: int = 2592000,  # 30天
        httponly: bool = True,
        cookie_name: str = "session",
        prefix: str = "session:",
        sessioncookie: bool = False,
        samesite: str = None,
        session_name: str = "session",
        secure: bool = False,
    ):
        """初始化用于在Tortoise ORM中存储客户端会话的接口。

        参数:
            domain (str, 可选): 将附加到cookie的可选域名。
            expiry (int, 可选): 会话过期的秒数。默认为30天。
            httponly (bool, 可选): 为会话cookie添加`httponly`标志。
            cookie_name (str, 可选): 用于客户端cookie的名称。
            prefix (str, 可选): 会话ID的前缀。
            sessioncookie (bool, 可选): 指定发送的cookie是否应为'会话cookie'。
            samesite (str, 可选): 设置SameSite cookie属性。
            session_name (str, 可选): 可通过请求访问的会话名称。
            secure (bool, 可选): 为会话cookie添加`Secure`标志。
        """
        super().__init__(
            expiry=expiry,
            prefix=prefix,
            cookie_name=cookie_name,
            domain=domain,
            httponly=True,
            sessioncookie=sessioncookie,
            samesite=samesite,
            session_name=session_name,
            secure=secure,
        )

    async def _get_value(self, prefix, sid):
        session = await Sessions.filter(id=f"{prefix}{sid}").first()
        if session:
            return ujson.dumps(session.data)
        return None

    async def _delete_key(self, key):
        await Sessions.filter(id=key).delete()

    async def _set_value(self, key, data):
        expiry = datetime.utcnow() + timedelta(seconds=self.expiry)
        await Sessions.update_or_create(
            defaults={"data": data, "expiry": expiry},
            id=key
        )

    @classmethod
    async def _cleanup_expired_sessions(cls):
        current_time = datetime.utcnow()
        await Sessions.filter(Q(expiry__lt=current_time)).delete()
