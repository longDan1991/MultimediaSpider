from datetime import datetime
from tortoise.fields import ReverseRelation, ManyToManyRelation
from tortoise.models import Model

def model_to_json(model, exclude_fields=None):
    """
    将模型对象转换为JSON可序列化的字典
    
    :param model: Tortoise ORM 模型实例
    :param exclude_fields: 要排除的字段列表
    :return: 可序列化的字典
    """
    if not isinstance(model, Model):
        return str(model)
    
    if exclude_fields is None:
        exclude_fields = []
    
    data = {}
    for field_name, field in model._meta.fields_map.items():
        if field_name in exclude_fields:
            continue
        
        value = getattr(model, field_name)
        
        if isinstance(value, datetime):
            data[field_name] = value.isoformat()
        elif isinstance(field, (ReverseRelation, ManyToManyRelation)):
            # 对于反向关系和多对多关系，我们跳过这些字段
            continue
        elif isinstance(value, Model):
            # 对于外键关系，只保存主键
            data[field_name] = value.pk
        else:
            data[field_name] = value
    
    return data