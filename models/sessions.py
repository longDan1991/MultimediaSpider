from tortoise import fields, Model

class Sessions(Model):
    id = fields.CharField(primary_key=True, max_length=64)
    data = fields.JSONField()
    expiry = fields.DatetimeField()

    class Meta:
        table = "sessions"