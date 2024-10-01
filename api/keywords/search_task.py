from api.keywords.xhs_notes import notes_task
from models.other.platform import Platform 
import asyncio
 
async def schedule_search_task(keyword, user, platforms):

    if Platform.XHS.value in platforms:
        asyncio.create_task(notes_task(keyword, user))

    return True
