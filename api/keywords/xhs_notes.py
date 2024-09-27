from management.medium.xhs.actions.notes import search_notes
from models.cookies import Cookies
from models.other.platform import Platform, PlatformStatus
from models.xhs.notes import XHSNotes
from models.xhs.keyword_notes import KeywordNotes
import asyncio
import random
from helpers.sanic import app
from datetime import datetime, timedelta


async def notes_task(keyword, user):
    cookies = await Cookies.filter(user=user, platform=Platform.XHS.value)
    if not cookies:
        await app.cancel_task(f"_notes_task_{keyword.id}")
        return True

    cookie = cookies[0].value

    platform_info = keyword.platform_info.get(Platform.XHS.value, PlatformStatus())
    last_update = platform_info.last_update
    last_page = platform_info.last_page
    max_page = platform_info.max_page

    # 检查是否在一天内更新过
    if last_update and datetime.now() - datetime.fromisoformat(last_update) < timedelta(
        days=1
    ):
        start_page = last_page + 1
    else:
        start_page = 1

    for page in range(start_page, max_page):
        if await _process_page(cookie, page, keyword):
            break

        # 更新平台信息
        platform_info.last_update = datetime.now().isoformat()
        platform_info.last_page = page
        keyword.platform_info[Platform.XHS.value] = platform_info
        await keyword.save()

    await app.cancel_task(f"_notes_task_{keyword.id}")
    return True


async def _process_page(cookie, page, keyword):
    await asyncio.sleep(random.randint(2, 5))
    results = await search_notes(keyword.value, cookie, page=page)
    if not results:
        return True

    notes_to_upsert = _extract_notes(results)
    if notes_to_upsert:
        await _upsert_notes(notes_to_upsert, keyword)

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


async def _upsert_notes(notes_to_upsert, keyword):
    try:
        ns = [XHSNotes(**note) for note in notes_to_upsert]
        await XHSNotes.bulk_create(
            ns,
            update_fields=[
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
            on_conflict=["notes_id"],
        )
    except Exception as e:
        print(f"批量创建XHSNotes时发生错误: {e}")
        return

    try:
        existing_notes = await XHSNotes.filter(
            notes_id__in=[note.notes_id for note in ns]
        )
        keyword_notes = [
            KeywordNotes(keyword=keyword, note=note) for note in existing_notes
        ]
        await KeywordNotes.bulk_create(keyword_notes, ignore_conflicts=True)
    except Exception as e:
        print(f"批量创建KeywordNotes时发生错误: {e}")
        print(f"existing_notes: {existing_notes}")
