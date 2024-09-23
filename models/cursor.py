from tortoise import Model, fields


class Cursor(Model):
    id = fields.IntField(primary_key=True)
    api_label = fields.CharField(max_length=100, description="API标签", unique=True)
    cursor = fields.TextField(description="断点续爬的游标")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "cursors"

    def __str__(self):
        return f"{self.api_label}: {self.cursor}"

