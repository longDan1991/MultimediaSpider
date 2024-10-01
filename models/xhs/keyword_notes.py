from tortoise import Model, fields 

class KeywordNotes(Model):
    id = fields.IntField(pk=True)
    keyword = fields.ForeignKeyField('models.Keywords', related_name='notes')
    note = fields.ForeignKeyField('models.XHSNotes', related_name='keywords')
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "keyword_notes"
        unique_together = ("keyword", "note")

    def __str__(self):
        return f"{self.keyword.value} - {self.note.id}"
