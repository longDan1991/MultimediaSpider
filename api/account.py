import json
from sanic import Blueprint, response
from helpers.authenticated import authenticated


account_bp = Blueprint("account", url_prefix="/account")


@account_bp.route("/")
@authenticated(fetchUserInfo=True)
async def get_account(request):

    user = request.ctx.user

    print("============", user)
    return response.json({"user": user.model_dump()})
