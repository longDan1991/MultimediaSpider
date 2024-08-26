from sanic import Blueprint, response
from helpers.authenticated import authenticated
from models.users import Users

task_bp = Blueprint("task", url_prefix="/task")


@task_bp.route("/")
@authenticated()
async def get_task_list(request):
    users = await Users.all()
    print("==========users", users)
    return response.json({"users": users})


@task_bp.route("/create")
@authenticated()
async def create_task(request):
    user = await Users.get(logtoId=request.ctx.user["sub"])

    print("===get_task_list=====", user)
    return response.json({"task": user})
