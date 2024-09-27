from typing import Dict
from management.medium.xhs.request import post
from management.medium.xhs.utils.search_id import get_search_id 
from models.xhs.notes import SearchSortType, SearchNoteType

async def search_notes(
    keyword: str,
    cookies: str,
    page: int = 1,
    page_size: int = 20,
    sort: SearchSortType = SearchSortType.GENERAL,
    note_type: SearchNoteType = SearchNoteType.ALL,
) -> Dict:
    """
    根据关键词搜索笔记
    """
    uri = "/api/sns/web/v1/search/notes"
    data = {
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
        "search_id": get_search_id(),
        "sort": sort.value,
        "note_type": note_type.value,
    }
    print("data======2", data)
    return await post(uri, cookies, data)