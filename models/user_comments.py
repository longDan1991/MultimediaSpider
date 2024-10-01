from tortoise import Model, fields

class UserComments(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField('models.User', related_name='comments')
    comment = fields.ForeignKeyField('models.xhs.comments.Comment', related_name='users')
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "user_comments"
        unique_together = ("user", "comment")

    def __str__(self):
        return f"{self.user.username} - {self.comment.id}"
