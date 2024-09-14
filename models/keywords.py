from tortoise import Model, fields


class Keywords(Model):
    id = fields.IntField(pk=True)
    value = fields.CharField(max_length=255)
    is_monitored = fields.BooleanField(default=True)
    is_deleted = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    search_results = fields.JSONField(null=True)

    class Meta:
        table = "keywords"

