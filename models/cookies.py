from tortoise import Model, fields


class Cookies(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.Users", related_name="user")
    value = fields.TextField()
    platform = fields.CharField(50)
    platform_account = fields.JSONField(null=True)
