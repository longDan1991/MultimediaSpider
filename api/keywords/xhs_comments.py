from management.medium.xhs.actions.comments import get_note_comments
from models.xhs.comments import Comment
from helpers.queue import enqueue_task
import asyncio 
from models.xhs.notes import XHSNotes
from models.keywords import Keywords
from models.user_comments import UserComments
from models.user_keyword import UserKeyword
from models.other.platform import Platform

async def process_comments(note_ids, keyword_id):
    tasks = [
        enqueue_task(
            fetch_and_store_comments,
            queue_name=f"comments_{note_id}",
            wait_for_result=False
        )(note_id, keyword_id)
        for note_id in note_ids
    ]
    await asyncio.gather(*tasks)

async def fetch_and_store_comments(note_id, keyword_id):
    note = await XHSNotes.get(notes_id=note_id)
    note.comments_call_times += 1

    if note.comments_call_times > 10:
        await note.save()
        return

    cursor = note.comments_cursor
    comments_data = await get_note_comments(note_id, cursor)
    if not comments_data or not comments_data.get("comments"):
        await note.save()
        return

    comments = comments_data.get("comments", [])
    await store_comments(comments, keyword_id)
    note.comments_cursor = comments_data.get("cursor", "")
    note.comments_has_more = comments_data.get("has_more", False)
    await note.save()

    if note.comments_has_more:
        asyncio.create_task(process_comments([note_id], keyword_id))

async def store_comments(comments, keyword_id):
    keyword = await Keywords.get(id=keyword_id).prefetch_related('user')
    user = keyword.user
    user_keyword = await UserKeyword.get(user=user, keyword=keyword)
    sub_keywords = set(user_keyword.sub_keywords)

    comments_to_create = []
    user_comments_to_create = []
    
    for comment in comments:
        comment_data = {
            "id": comment.get("id"),
            "note_id": comment.get("note_id"),
            "user_id": comment.get("user", {}).get("user_id"),
            "nickname": comment.get("user", {}).get("nickname"),
            "avatar": comment.get("user", {}).get("avatar"),
            "content": comment.get("content"),
            "ip_location": comment.get("ip_location"),
            "status": comment.get("status"),
            "liked": comment.get("liked"),
            "like_count": comment.get("like_count"),
            "create_time": comment.get("create_time"),
            "sub_comment_count": comment.get("sub_comment_count"),
            "sub_comment_cursor": comment.get("sub_comment_cursor"),
            "sub_comment_has_more": comment.get("sub_comment_has_more"),
            "platform": Platform.XHS.value
        }
        new_comment = Comment(**comment_data)
        comments_to_create.append(new_comment)

        if any(sub_keyword in comment_data["content"] for sub_keyword in sub_keywords):
            user_comments_to_create.append(UserComments(user=user, comment=new_comment))

    await Comment.bulk_create(comments_to_create)
    if user_comments_to_create:
        await UserComments.bulk_create(user_comments_to_create)
