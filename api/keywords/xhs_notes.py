from management.medium.xhs.actions.notes import search_notes
from models.cookies import Cookies
from models.other.platform import Platform
from models.xhs.notes import XHSNotes
from models.xhs.keyword_notes import KeywordNotes
import asyncio
import random
from models.keywords import Keywords
from helpers.queue import enqueue_task
from api.keywords.xhs_comments import process_comments

async def notes_task(keyword, user):
    cookies = await Cookies.filter(user=user, platform=Platform.XHS.value)
    if not cookies:
        return True

    cookie = cookies[0].value

    platform_info = keyword.platform_info.get(Platform.XHS.value)
    max_page = platform_info["max_page"]
    start_page = platform_info["start_page"]

    for page in range(start_page, start_page + max_page):
        if await _process_page(cookie, page, keyword):
            break

    return True


async def _process_page(cookie, page, keyword):
    await asyncio.sleep(random.randint(2, 5))
    results = await search_notes(keyword.value, cookie, page=page)
    if not results:
        return True

    notes_to_upsert = _extract_notes(results)
    if notes_to_upsert:
        await enqueue_task(_upsert_notes_in_queue, wait_for_result=False)(
            notes_to_upsert,
            keyword.id,
        )

    return not results.get("has_more", False)


def _extract_notes(results):
    notes_to_upsert = []
    for item in results.get("items", []):
        if item.get("model_type") == "note":
            note_card = item.get("note_card", {})
            user = note_card.get("user", {})
            interact_info = note_card.get("interact_info", {})
            notes_to_upsert.append(
                {
                    "notes_id": item.get("id"),
                    "model_type": item.get("model_type"),
                    "xsec_token": item.get("xsec_token"),
                    "type": note_card.get("type"),
                    "display_title": note_card.get("display_title"),
                    "user_id": user.get("user_id"),
                    "nickname": user.get("nickname"),
                    "avatar": user.get("avatar"),
                    "liked": interact_info.get("liked"),
                    "liked_count": interact_info.get("liked_count"),
                }
            )
    return notes_to_upsert


async def _upsert_notes_in_queue(notes_to_upsert, keyword_id):
    try:
        # 批量创建或更新 XHSNotes
        notes_ids = [note["notes_id"] for note in notes_to_upsert]
        existing_notes = await XHSNotes.filter(notes_id__in=notes_ids)
        existing_notes_dict = {note.notes_id: note for note in existing_notes}

        notes_to_create = []
        notes_to_update = []
        for note_data in notes_to_upsert:
            if note_data["notes_id"] in existing_notes_dict:
                note = existing_notes_dict[note_data["notes_id"]]
                for key, value in note_data.items():
                    setattr(note, key, value)
                notes_to_update.append(note)
            else:
                notes_to_create.append(XHSNotes(**note_data))

        if notes_to_create:
            await XHSNotes.bulk_create(notes_to_create)
            asyncio.create_task(process_comments([note["notes_id"] for note in notes_to_create], keyword_id))
        if notes_to_update:
            await XHSNotes.bulk_update(
                notes_to_update,
                fields=[
                    "model_type",
                    "xsec_token",
                    "type",
                    "display_title",
                    "user_id",
                    "nickname",
                    "avatar",
                    "liked",
                    "liked_count",
                    "updated_at",
                ],
            )

        # 获取关键词对象
        keyword = await Keywords.get(id=keyword_id)

        # 获取已存在的关键词-笔记关联
        existing_keyword_notes = set(
            await KeywordNotes.filter(
                keyword=keyword, note__in=existing_notes
            ).values_list("note_id", flat=True)
        )

        # 创建新的关键词-笔记关联
        new_keyword_notes = [
            KeywordNotes(keyword=keyword, note_id=note.id)
            for note in existing_notes
            if note.id not in existing_keyword_notes
        ]
        if new_keyword_notes:
            await KeywordNotes.bulk_create(new_keyword_notes)

    except Exception as e:
        print(f"更新笔记时发生错误: {e}")
        # 可以考虑添加更详细的错误日志或异常处理
