from sanic import Blueprint, response
from models.user_comments import UserComments
from api.auth import authenticated
from models.users import Users
from tortoise.exceptions import DoesNotExist

comments_bp = Blueprint("comments", url_prefix="/comments")

@comments_bp.route("/", methods=["GET"]) 
@authenticated()
async def get_comments_by_keyword(request, page: int = 1, page_size: int = 20):
    try:
        user = await Users.get(logtoId=request.ctx.user["sub"])
    except DoesNotExist:
        return response.json({"message": "用户不存在"}, status=404)

    try:
        query = UserComments.filter(user=user).prefetch_related('comment')
        total_count = await query.count()
        user_comments = await query.offset((page - 1) * page_size).limit(page_size)
        
        data = [{
            "id": uc.comment.id,
            "note_id": uc.comment.note_id,
            "user_id": uc.comment.user_id,
            "nickname": uc.comment.nickname,
            "content": uc.comment.content,
            "create_time": uc.comment.create_time,
            "like_count": uc.comment.like_count,
            "avatar": uc.comment.avatar,
            "ip_location": uc.comment.ip_location,
            "status": uc.comment.status,
            "liked": uc.comment.liked,
            "platform": uc.comment.platform
        } for uc in user_comments]
        
        return response.json({
            "data": data,
            "pagination": {
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }, status=200)
    
    except Exception as e:
        return response.json({"message": f"发生错误：{str(e)}"}, status=500)
