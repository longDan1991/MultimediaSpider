from tortoise import Model, fields

class XHSNotes(Model):
    id = fields.CharField(max_length=255, primary_key=True)
    model_type = fields.CharField(max_length=50)
    xsec_token = fields.CharField(max_length=255)
    
    # note_card 字段
    type = fields.CharField(max_length=50)
    display_title = fields.CharField(max_length=255, null=True)
    
    # user 字段
    user_id = fields.CharField(max_length=255)
    nickname = fields.CharField(max_length=255)
    avatar = fields.CharField(max_length=1024)
    
    # interact_info 字段
    liked = fields.BooleanField()
    liked_count = fields.CharField(max_length=50) 
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "xhs_notes"

