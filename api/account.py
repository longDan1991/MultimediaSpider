import json
from sanic import Blueprint, response
from helpers.authenticated import authenticated
from models.cookies import Cookies
from models.users import Users
from tortoise.exceptions import DoesNotExist


account_bp = Blueprint("account", url_prefix="/account")


@account_bp.route("/")
@authenticated()
async def get_account(request):
    logto = request.ctx.user
    try:
        user = await Users.get(logtoId=logto["sub"])
    except DoesNotExist:
        user = await Users.create(logtoId=logto["sub"], name="hello")

    cookies = await Cookies.all().filter(user=user)

    # 正确返回用户信息
    user_data = {
        "id": user.id,
        "name": user.name,
        "logtoId": user.logtoId
    }

    return response.json({
        "user": user_data,
        "cookies": [{"id": cookie.id, "value": cookie.value} for cookie in cookies]
    })
