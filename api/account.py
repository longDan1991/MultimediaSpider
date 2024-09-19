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

    user_data = {"name": user.name, "logtoId": user.logtoId}
    return response.json(
        {
            "data": {
                "user": user_data,
                "cookies": [
                    {
                        "id": cookie.id,
                        "value": cookie.value,
                        "platform": cookie.platform,
                        "platform_account": cookie.platform_account
                    } for cookie in cookies
                ],
            }
        }
    )


@account_bp.route("/store-cookie", methods=["POST"])
async def store_cookie(request):
    data = request.json
    logtoId = data.get("logtoId")
    cookie_value = data.get("cookies")
    platform = data.get("platform")

    try:
        user = await Users.get(logtoId=logtoId)
    except DoesNotExist:
        return response.json({"message": "用户不存在"}, status=404)

    cookies = await Cookies.filter(user=user, platform=platform)
    if cookies:
        cookie = cookies[0]
        cookie.value = cookie_value
        await cookie.save()
    else:
        cookie = await Cookies.create(user=user, platform=platform, value=cookie_value, platform_account=dict())

    return response.json(
        {
            "data": cookie.id,
        },
        status=201,
    )
