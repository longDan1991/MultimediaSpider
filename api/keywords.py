from sanic import Blueprint, response
from helpers.authenticated import authenticated
from management.medium.xhs.actions.search import search_notes
from models.cookies import Cookies
from models.keywords import Keywords
from tortoise.exceptions import DoesNotExist

from models.tasks import Platform
from models.users import Users

keywords_bp = Blueprint("keywords", url_prefix="/keywords")


@keywords_bp.route("/", methods=["GET"])
@authenticated()
async def get_keywords(request):
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 10))
    offset = (page - 1) * page_size

    total_count = await Keywords.all().count()
    keywords = await Keywords.all().offset(offset).limit(page_size)

    return response.json(
        {
            "data": [
                {
                    "id": keyword.id,
                    "value": keyword.value,
                    "is_monitored": keyword.is_monitored,
                    "is_deleted": keyword.is_deleted,
                    "created_at": keyword.created_at.isoformat(),
                    "updated_at": keyword.updated_at.isoformat(),
                    "search_results": keyword.search_results,
                }
                for keyword in keywords
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
    is_deleted = data.get("is_deleted", False)
    search_results = data.get("search_results", {})

    if not search_results:
        return response.json({"message": "至少选择一个平台"}, status=400)

    logto = request.ctx.user
    try:
        user = await Users.get(logtoId=logto["sub"])
    except DoesNotExist:
        return response.json({"message": "用户不存在"}, status=404)

    if (
        Platform.XHS.value in search_results
        or Platform.XHS.value in search_results.keys()
    ):
        print("xhs_results======1", search_results)
        cookies = await Cookies.filter(user=user, platform=Platform.XHS.value)
        if not cookies:
            return response.json({"message": "未找到小红书cookie"}, status=404)
        xhs_results = await search_notes(value, cookies[0].value)
        print("xhs_results======20", xhs_results)
        if xhs_results:
            search_results[Platform.XHS.value] = xhs_results

    keyword = await Keywords.create(
        value=value,
        is_monitored=is_monitored,
        is_deleted=is_deleted,
        search_results=search_results,
        user=user,
    )

    return response.json(
        {
            "data": {
                "id": keyword.id,
                "value": keyword.value,
                "is_monitored": keyword.is_monitored,
                "is_deleted": keyword.is_deleted,
                "created_at": keyword.created_at.isoformat(),
                "updated_at": keyword.updated_at.isoformat(),
                "search_results": keyword.search_results,
            }
        },
        status=201,
    )


@keywords_bp.route("/<keyword_id:int>", methods=["PUT"])
@authenticated()
async def update_keyword(request, keyword_id):
    data = request.json
    try:
        keyword = await Keywords.get(id=keyword_id)
        keyword.value = data.get("value", keyword.value)
        keyword.is_monitored = data.get("is_monitored", keyword.is_monitored)
        await keyword.save()
        return response.json(
            {
                "data": {
                    "id": keyword.id,
                    "value": keyword.value,
                    "is_monitored": keyword.is_monitored,
                }
            }
        )
    except DoesNotExist:
        return response.json({"message": "关键词不存在"}, status=404)


@keywords_bp.route("/<keyword_id:int>", methods=["DELETE"])
@authenticated()
async def delete_keyword(request, keyword_id):
    try:
        keyword = await Keywords.get(id=keyword_id)
        await keyword.delete()
        return response.json({"message": "关键词已删除"})
    except DoesNotExist:
        return response.json({"message": "关键词不存在"}, status=404)
