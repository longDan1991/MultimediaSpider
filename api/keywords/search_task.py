from management.medium.xhs.actions.search import search_notes
from models.cursor import Cursor
from models.xhs.notes import XHSNotes
import asyncio
import random
from helpers.sanic import app
from tortoise.transactions import atomic
from tortoise.functions import Count

async def xhs_notes_task(value, cookies):
    cursor_obj, created = await Cursor.get_or_create(
        api_label="xhs_notes", defaults={"cursor": "1"}
    )
    cursor = cursor_obj.cursor
    call_count = 0
    while call_count < 10:
        await asyncio.sleep(random.randint(1, 30))
        xhs_results = await search_notes(value, cookies[0].value, page=int(cursor))
        if xhs_results:
            notes_to_upsert = []
            for item in xhs_results.get("items", []):
                if item.get("model_type") == "note":
                    note_card = item.get("note_card", {})
                    notes_to_upsert.append({
                        "id": item.get("id"),
                        "model_type": item.get("model_type"),
                        "xsec_token": item.get("xsec_token"),
                        "type": note_card.get("type"),
                        "display_title": note_card.get("display_title"),
                        "user_id": note_card.get("user", {}).get("user_id"),
                        "nickname": note_card.get("user", {}).get("nickname"),
                        "avatar": note_card.get("user", {}).get("avatar"),
                        "liked": note_card.get("interact_info", {}).get("liked"),
                        "liked_count": note_card.get("interact_info", {}).get("liked_count")
                    })
            
            if notes_to_upsert:
                await XHSNotes.bulk_create(
                    [XHSNotes(**note) for note in notes_to_upsert],
                    update_fields=[
                        "model_type", "xsec_token", "type", "display_title",
                        "user_id", "nickname", "avatar", "liked", "liked_count"
                    ],
                    on_conflict=["id"]
                )
            
            if not xhs_results.get("has_more", False):
                break
            cursor = str(int(cursor) + 1)
        call_count += 1

    cursor_obj.cursor = cursor
    await cursor_obj.save()
    app.cancel_task("_xhs_notes_task")
