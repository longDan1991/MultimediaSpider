import math
from sanic import Blueprint, response
from helpers.authenticated import authenticated
from models.users import Users

task_bp = Blueprint("task", url_prefix="/task")


@task_bp.route("/")
@authenticated()
async def get_task_list(request):
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    total_users = await Users.all().count()

    start_index = (page - 1) * per_page

    users = await Users.all().offset(start_index).limit(per_page)

    headers = {"x-total-count": str(total_users)}

    return response.json(
        users,
        headers=headers,
    )


@task_bp.route("/create", methods=["POST"])
@authenticated()
async def create_task(request):
    logtoId = request.ctx.user["sub"]

    user = await Users.get(logtoId=logtoId)

    if not user:
        user = await Users.create(logtoId=logtoId)

    # task = await Task.create(user=user)

    return response.json({"task_id": 0})
