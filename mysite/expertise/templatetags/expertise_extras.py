from django import template

register = template.Library()


@register.simple_tag
def formatted_node_pk(label, pk):
    return f"{label[:4]}-{pk}"