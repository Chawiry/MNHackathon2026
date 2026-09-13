from django import template

register = template.Library()


@register.filter
def threshold_tone(value):
    """Map a 0-100 score to a semantic tone using the app's 80/60 convention."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "neutral"
    if value >= 80:
        return "success"
    if value >= 60:
        return "warning"
    return "danger"


@register.simple_tag
def nav_active(request, *url_names):
    """Return the 'active' class when the current view matches any url name."""
    match = getattr(request, "resolver_match", None)
    if match is not None and match.url_name in url_names:
        return "active"
    return ""