from tortoise import Model, fields


class Cookies(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.Users", related_name="user")
    url = fields.CharField(50)
    value = fields.TextField()
