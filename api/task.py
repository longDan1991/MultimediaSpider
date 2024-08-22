from sanic import Blueprint, json, redirect
from helpers.authenticated import authenticated
from helpers.nocodb import get_tasks

task_bp = Blueprint("task", url_prefix="/task")


@task_bp.route("/")
@authenticated()
async def get_task_list(request):
    result = await get_tasks({})

    print("===get_task_list=====", result)
    return json({"task": result})
