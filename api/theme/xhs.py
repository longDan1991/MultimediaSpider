from sanic import Blueprint 
from helpers.mode import model_to_json
from models.xhs.keyword_notes import KeywordNotes 

async def get_xhs_notes(keyword_id, page, page_size):
    offset = (page - 1) * page_size 

    total_count = await KeywordNotes.filter(keyword_id=keyword_id).count()
    notes = (
        await KeywordNotes.filter(keyword_id=keyword_id)
        .offset(offset)
        .limit(page_size)
        .prefetch_related("note")
    )
    notes_data = [model_to_json(kn.note, exclude_fields=["keywords"]) for kn in notes]

    return notes_data, total_count
