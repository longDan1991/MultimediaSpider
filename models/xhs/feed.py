from tortoise import Model, fields

class XHSFeed(Model):
    id = fields.CharField(max_length=255, pk=True)
    model_type = fields.CharField(max_length=50)
    
    # note_card 字段
    time = fields.BigIntField()
    last_update_time = fields.BigIntField()
    note_id = fields.CharField(max_length=255)
    type = fields.CharField(max_length=50)
    title = fields.CharField(max_length=255, null=True)
    desc = fields.TextField(null=True)
    
    # user 字段
    user_id = fields.CharField(max_length=255)
    nickname = fields.CharField(max_length=255)
    avatar = fields.CharField(max_length=1024)
    
    # interact_info 字段
    liked = fields.BooleanField()
    liked_count = fields.CharField(max_length=50)
    collected = fields.BooleanField()
    collected_count = fields.CharField(max_length=50)
    comment_count = fields.CharField(max_length=50)
    share_count = fields.CharField(max_length=50)
    followed = fields.BooleanField()
    relation = fields.CharField(max_length=50)
    
    # 其他字段
    cursor_score = fields.CharField(max_length=255, null=True)
    
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "xhs_feed"

class XHSImage(Model):
    id = fields.IntField(pk=True)
    feed = fields.ForeignKeyField('models.XHSFeed', related_name='images')
    file_id = fields.CharField(max_length=255, null=True)
    height = fields.IntField()
    width = fields.IntField()
    trace_id = fields.CharField(max_length=255, null=True)
    url_pre = fields.CharField(max_length=1024)
    url_default = fields.CharField(max_length=1024)
    live_photo = fields.BooleanField()

    class Meta:
        table = "xhs_images"

class XHSTag(Model):
    id = fields.CharField(max_length=255, pk=True)
    name = fields.CharField(max_length=255)
    type = fields.CharField(max_length=50)

    class Meta:
        table = "xhs_tags"

class XHSFeedTag(Model):
    feed = fields.ForeignKeyField('models.XHSFeed', related_name='tags')
    tag = fields.ForeignKeyField('models.XHSTag', related_name='feeds')

    class Meta:
        table = "xhs_feed_tags"
