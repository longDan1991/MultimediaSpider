from sanic import Blueprint

from api.auth import auth_bp
from api.account import account_bp
from api.keywords.keywords import keywords_bp
from api.theme.theme import theme_bp

api = Blueprint.group(auth_bp, account_bp, keywords_bp, theme_bp, url_prefix="/api")
