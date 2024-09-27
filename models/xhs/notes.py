from tortoise import Model, fields
from enum import Enum

class NoteType(Enum):
    NORMAL = "normal"
    VIDEO = "video"


class SearchSortType(Enum):
    """search sort type"""
    # default
    GENERAL = "general"
    # most popular
    MOST_POPULAR = "popularity_descending"
    # Latest
    LATEST = "time_descending"


class SearchNoteType(Enum):
    """search note type
    """
    # default
    ALL = 0
    # only video
    VIDEO = 1
    # only image
    IMAGE = 2
    

class XHSNotes(Model):
    id = fields.IntField(primary_key=True)
    notes_id = fields.CharField(max_length=255, unique=True)

    model_type = fields.CharField(max_length=50)
    xsec_token = fields.CharField(max_length=255)
    
    # note_card 字段
    type = fields.CharField(max_length=50)
    display_title = fields.CharField(max_length=255, null=True)
    
    # user 字段
    user_id = fields.CharField(max_length=255)
    nickname = fields.CharField(max_length=255)
    avatar = fields.CharField(max_length=1024)
    
    # interact_info 字段
    liked = fields.BooleanField()
    liked_count = fields.CharField(max_length=50) 
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "xhs_notes" 

