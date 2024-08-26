from tortoise import Model, fields


class Cookies(Model):
    id = fields.IntField(pk=True)
    platform = fields.CharField(50)
    user = fields.ForeignKeyField("models.users.Users", related_name="user")

    def __str__(self):
        return f"I am {self.name}"
