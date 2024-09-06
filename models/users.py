from tortoise import Model, fields


class Users(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(50)
    logtoId = fields.CharField(50)

    class Meta:
        table = "users"
