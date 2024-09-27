from tortoise import Model, fields

class Keywords(Model):
    id = fields.IntField(primary_key=True)
    value = fields.CharField(max_length=255)
    platform_info = fields.JSONField(default=dict)  # 新增的JSON字段，用于存储平台信息

    class Meta:
        table = "keywords"

