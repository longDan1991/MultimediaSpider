import math
from sanic import Blueprint, response
from helpers.authenticated import authenticated
from models.users import Users
from models.tasks import Tasks, TaskDetails
from tortoise.expressions import Q

task_bp = Blueprint("task", url_prefix="/task")


@task_bp.route("/")
@authenticated()
async def get_task_list(request):
    start = int(request.args.get('_start', 0))
    end = int(request.args.get('_end', 10))
    
    total = await Tasks.all().count()
    
    tasks = await Tasks.all().offset(start).limit(end - start)
    
    task_list = [
        {
            "id": task.id,
            "platform": task.platform,
            "crawler_type": task.crawler_type,
            "data": task.data
        }
        for task in tasks
    ]
    
    return response.json(task_list, headers={"X-Total-Count": str(total)})


@task_bp.route("/create", methods=["POST"])
@authenticated()
async def create_task(request):
    data = request.json
    
    task_details = TaskDetails(**data.get("task_details", {}))
    
    new_task = await Tasks.create(
        platform=data.get("platform"),
        crawler_type=data.get("crawler_type"),
        data=task_details.dict()
    )
    
    return response.json({ 
        "task_id": new_task.id
    }, status=201)
