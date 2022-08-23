from django import template
from django.contrib.auth import get_user_model
register = template.Library()

@register.filter(name='get_user')
def get_user(user_id):
    try:
        return get_user_model().objects.get(id=user_id)
    except:
        return
