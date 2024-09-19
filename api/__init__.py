from sanic import Blueprint

from api.auth import auth_bp
from api.task import task_bp
from api.account import account_bp
from api.keywords import keywords_bp

api = Blueprint.group(auth_bp, task_bp, account_bp, keywords_bp, url_prefix="/api")
