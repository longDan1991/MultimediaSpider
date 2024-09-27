from api.keywords.xhs_notes import notes_task 
from helpers.sanic import app
from sanic.exceptions import SanicException
from models.other.platform import Platform


def _check_task_exists(name, cb):
    try:
        app.get_task(name)
    except (KeyError, SanicException):
        app.add_task(cb, name=name)


def schedule_search_task(keyword, user, platforms):

    if Platform.XHS.value in platforms:
        _check_task_exists(f"_notes_task_{keyword.id}", notes_task(keyword, user))

    return True
