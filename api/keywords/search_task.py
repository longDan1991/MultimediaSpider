from management.medium.xhs.actions.search import search_notes
from models.keywords import Keywords
from models.xhs.notes import XHSNotes
import asyncio
import random
from helpers.sanic import app
from datetime import datetime
from sanic.exceptions import SanicException 


async def notes_task(keyword_value, cookie):

    async def process_page(page):
        await asyncio.sleep(random.randint(2, 5))
        results = await search_notes(keyword_value, cookie, page=page)
        if results:
            notes_to_upsert = []
            for item in results.get("items", []):
                if item.get("model_type") == "note":
                    note_card = item.get("note_card", {})
                    user = item.get("user", {})
                    interact_info = item.get("interact_info", {})
                    notes_to_upsert.append(
                        {
                            "id": item.get("id"),
                            "search_keyword": keyword_value,
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

            if notes_to_upsert:
                await XHSNotes.bulk_create(
                    [XHSNotes(**note) for note in notes_to_upsert],
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
                    ],
                    on_conflict=["id"],
                )
        return not results.get("has_more", False)

    for page in range(1, 11):
        if await process_page(page):
            break

    await Keywords.filter(value=keyword_value).update(last_search=datetime.now())

    app.cancel_task(f"_notes_task_{keyword_value}")


def schedule_notes_task(keyword_value, cookie):
    try:
        app.get_task(f"_notes_task_{keyword_value}")
    except (KeyError, SanicException): 
        app.add_task(
            notes_task(keyword_value, cookie),
            name=f"_notes_task_{keyword_value}",
        )
