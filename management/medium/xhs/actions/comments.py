from typing import Dict
from management.medium.xhs.request import get


async def get_note_comments(note_id: str, cursor: str = "") -> Dict:
    uri = "/api/sns/web/v2/comment/page"
    params = {
        "note_id": note_id,
        "cursor": cursor,
        "top_comment_id": "",
        "image_formats": "jpg,webp,avif",
    }
    return await get(uri, params)


async def get_note_sub_comments(
    note_id: str, root_comment_id: str, num: int = 10, cursor: str = ""
):
    """
    获取指定父评论下的子评论的API
    Args:
        note_id: 子评论的帖子ID
        root_comment_id: 根评论ID
        num: 分页数量
        cursor: 分页游标

    Returns:

    """
    uri = "/api/sns/web/v2/comment/sub/page"
    params = {
        "note_id": note_id,
        "root_comment_id": root_comment_id,
        "num": num,
        "cursor": cursor,
    }
    return get(uri, params)
