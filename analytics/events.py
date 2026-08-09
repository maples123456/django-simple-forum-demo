from .models import AnalyticsEvent


def record_event(event_name, *, user=None, board=None, post=None, source=AnalyticsEvent.Source.DJANGO, anonymous_id='', session_id='', properties=None):
    if user is not None and not getattr(user, 'is_authenticated', True):
        user = None
    return AnalyticsEvent.objects.create(
        event_name=event_name,
        user=user,
        board=board,
        post=post,
        source=source,
        anonymous_id=anonymous_id[:64],
        session_id=session_id[:64],
        properties=properties or {},
    )
