from tortoise import fields
from tortoise.models import Model

class Comment(Model):
    id = fields.CharField(max_length=24, pk=True)
    note_id = fields.CharField(max_length=24)
    user_id = fields.CharField(max_length=24)
    nickname = fields.CharField(max_length=50)
    avatar = fields.CharField(max_length=255)
    content = fields.TextField()
    ip_location = fields.CharField(max_length=50, null=True)
    status = fields.IntField()
    liked = fields.BooleanField()
    like_count = fields.IntField()
    create_time = fields.BigIntField()
    sub_comment_count = fields.IntField()
    sub_comment_cursor = fields.CharField(max_length=24, null=True)
    sub_comment_has_more = fields.BooleanField()
    platform = fields.CharField(max_length=20)

    class Meta:
        table = "xhs_comments"