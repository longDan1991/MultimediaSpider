from sanic import Blueprint, response
from helpers.authenticated import authenticated
from models.cookies import Cookies
from models.keywords import Keywords
from tortoise.exceptions import DoesNotExist
from models.tasks import Platform
from models.user_keyword import UserKeyword
from models.users import Users
from api.keywords.search_task import schedule_notes_task

keywords_bp = Blueprint("keywords", url_prefix="/keywords")


@keywords_bp.route("/", methods=["GET"])
@authenticated()
async def get_keywords(request):
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))
    offset = (page - 1) * page_size

    logto = request.ctx.user
    try:
        user = await Users.get(logtoId=logto["sub"])
    except DoesNotExist:
        return response.json({"message": "用户不存在"}, status=404)

    total_count = await UserKeyword.filter(user=user).count()
    user_keywords = await UserKeyword.filter(user=user).offset(offset).limit(page_size).prefetch_related('keyword')

    return response.json(
        {
            "data": [
                {
                    "id": uk.keyword.id,
                    "value": uk.keyword.value,
                    "is_monitored": uk.is_monitored,
                    "created_at": uk.created_at.isoformat(),
                    "updated_at": uk.updated_at.isoformat(),
                    "platforms": uk.platforms,
                    "platform_info": uk.keyword.platform_info,
                }
                for uk in user_keywords
            ],
            "pagination": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size,
            },
        }
    )

@keywords_bp.route("/", methods=["POST"])
@authenticated()
async def create_keyword(request):
    data = request.json
    value = data.get("value")
    is_monitored = data.get("is_monitored", True)
    platforms = data.get("platforms", [])

    if not platforms:
        return response.json({"message": "至少选择一个平台"}, status=400)

    logto = request.ctx.user
    try:
        user = await Users.get(logtoId=logto["sub"])
    except DoesNotExist:
        return response.json({"message": "用户不存在"}, status=404) 

    keyword, created = await Keywords.get_or_create(value=value)
    
    user_keyword, created = await UserKeyword.get_or_create(
        user=user,
        keyword=keyword,
        defaults={
            "is_monitored": is_monitored,
            "platforms": platforms
        }
    )

    if not created:
        return response.json({"message": "该关键词已存在"}, status=400)

    await schedule_notes_task(keyword, user)

    return response.json(
        {
            "data": {
                "id": keyword.id,
                "value": keyword.value,
                "is_monitored": user_keyword.is_monitored,
                "created_at": user_keyword.created_at.isoformat(),
                "updated_at": user_keyword.updated_at.isoformat(),
                "platforms": user_keyword.platforms,
                "platform_info": keyword.platform_info,
            }
        },
        status=201,
    )


@keywords_bp.route("/<keyword_id:int>", methods=["PUT"])
@authenticated()
async def update_keyword(request, keyword_id):
    data = request.json
    logto = request.ctx.user
    try:
        user = await Users.get(logtoId=logto["sub"])
        user_keyword = await UserKeyword.get(user=user, keyword_id=keyword_id)
        user_keyword.is_monitored = data.get("is_monitored", user_keyword.is_monitored)
        user_keyword.platforms = data.get("platforms", user_keyword.platforms)
        await user_keyword.save()
        return response.json(
            {
                "data": {
                    "id": user_keyword.keyword.id,
                    "value": user_keyword.keyword.value,
                    "is_monitored": user_keyword.is_monitored,
                    "platforms": user_keyword.platforms,
                    "platform_info": user_keyword.keyword.platform_info,
                }
            }
        )
    except DoesNotExist:
        return response.json({"message": "关键词不存在"}, status=404)


@keywords_bp.route("/<keyword_id:int>", methods=["DELETE"])
@authenticated()
async def delete_keyword(request, keyword_id):
    logto = request.ctx.user
    try:
        user = await Users.get(logtoId=logto["sub"])
        user_keyword = await UserKeyword.get(user=user, keyword_id=keyword_id)
        await user_keyword.delete()
        return response.json({"message": "关键词已删除"})
    except DoesNotExist:
        return response.json({"message": "关键词不存在"}, status=404)
