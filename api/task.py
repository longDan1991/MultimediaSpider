from urllib import response
from sanic import Blueprint, redirect
from helpers.authenticated import authenticated

task_bp = Blueprint("task", url_prefix="/task")


@task_bp.route("/setup")
@authenticated(shouldRedirect=True, fetchUserInfo=True)
async def protected_route(request):

    user = request.ctx.user
    return response.json({"message": "This route is protected", "user": user})
