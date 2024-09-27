from sanic import Blueprint, response
from api.theme.xhs import get_xhs_notes 
from models.user_keyword import UserKeyword
from models.users import Users 
from tortoise.exceptions import DoesNotExist
from helpers.authenticated import authenticated

theme_bp = Blueprint("theme", url_prefix="/theme")

async def get_theme_data(request, get_notes_func):
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))
    keyword_id = request.args.get("keyword_id")
    if not keyword_id:
        return response.json({"error": "keyword_id是必需的参数"}, status=400)

    # 获取当前用户
    logto = request.ctx.user
    try:
        user = await Users.get(logtoId=logto["sub"])
    except DoesNotExist:
        return response.json({"error": "用户不存在"}, status=404)

    # 检查关键词是否属于当前用户
    user_keyword = await UserKeyword.filter(keyword_id=keyword_id, user=user).first()
    if not user_keyword:
        return response.json({"error": "无权访问该关键词"}, status=403)

    notes_data, total_count = await get_notes_func(keyword_id, page, page_size)
     
    return response.json(
        {
            "data": notes_data,
            "pagination": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size,
            },
        }
    )

@theme_bp.route("/xhs", methods=["GET"])
@authenticated()
async def get_xhs_theme(request):
    return await get_theme_data(request, get_xhs_notes)

# @theme_bp.route("/douyin", methods=["GET"])
# @authenticated()
# async def get_douyin_theme(request):
#     return await get_theme_data(request, get_douyin_notes)
