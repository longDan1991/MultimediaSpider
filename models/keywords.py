from tortoise import Model, fields

class Keywords(Model):
    id = fields.IntField(primary_key=True)
    value = fields.CharField(max_length=255)
    platform_info = fields.JSONField(default=dict)

    class Meta:
        table = "keywords"

