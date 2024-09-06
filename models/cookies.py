from tortoise import Model, fields


class Cookies(Model):
    id = fields.IntField(pk=True)
    platform = fields.CharField(50)
    user = fields.ForeignKeyField("models.Users", related_name="user")
 
