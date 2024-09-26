from tortoise import Model, fields


class UserKeyword(Model):
    id = fields.IntField(primary_key=True)
    user = fields.ForeignKeyField("models.Users", related_name="user_keywords")
    keyword = fields.ForeignKeyField("models.Keywords", related_name="user_keywords")
    is_monitored = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    platforms = fields.JSONField(default=list)

    class Meta:
        table = "user_keyword"
        unique_together = ("user", "keyword")

    def __str__(self):
        return f"{self.user.username} - {self.keyword.value}"
