from api.keywords.xhs_notes import notes_task
from models.tasks import Platform
from helpers.sanic import app
from sanic.exceptions import SanicException


def _check_task_exists(name, cb):
    try:
        app.get_task(name)
    except (KeyError, SanicException):
        app.add_task(cb, name=name)


async def schedule_search_task(keyword, user):
    platforms = keyword.platforms

    if Platform.XHS.value in platforms:
        _check_task_exists(
            f"_notes_task_{keyword.id}", notes_task(keyword, user)
        ) 

    return True
