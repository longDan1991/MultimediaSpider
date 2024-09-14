from sanic import Blueprint, response
from helpers.authenticated import authenticated
from models.keywords import Keywords
from tortoise.exceptions import DoesNotExist

keywords_bp = Blueprint("keywords", url_prefix="/keywords")

@keywords_bp.route("/", methods=["GET"])
@authenticated()
async def get_keywords(request):
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    offset = (page - 1) * page_size

    total_count = await Keywords.all().count()
    keywords = await Keywords.all().offset(offset).limit(page_size)

    return response.json({
        "data": [{
            "id": keyword.id,
            "value": keyword.value,
            "is_monitored": keyword.is_monitored,
            "is_deleted": keyword.is_deleted,
            "created_at": keyword.created_at.isoformat(),
            "updated_at": keyword.updated_at.isoformat(),
            "search_results": keyword.search_results
        } for keyword in keywords],
        "pagination": {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
    })

@keywords_bp.route("/", methods=["POST"])
@authenticated()
async def create_keyword(request):
    data = request.json
    value = data.get("value")
    is_monitored = data.get("is_monitored", True)

    keyword = await Keywords.create(value=value, is_monitored=is_monitored)
    return response.json({
        "data": {"id": keyword.id, "value": keyword.value, "is_monitored": keyword.is_monitored}
    }, status=201)

@keywords_bp.route("/<keyword_id:int>", methods=["PUT"])
@authenticated()
async def update_keyword(request, keyword_id):
    data = request.json
    try:
        keyword = await Keywords.get(id=keyword_id)
        keyword.value = data.get("value", keyword.value)
        keyword.is_monitored = data.get("is_monitored", keyword.is_monitored)
        await keyword.save()
        return response.json({
            "data": {"id": keyword.id, "value": keyword.value, "is_monitored": keyword.is_monitored}
        })
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
