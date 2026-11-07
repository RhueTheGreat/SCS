from functools import wraps
from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from . import models


class AccountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.account = None
        account_id = request.session.get('account_id')
        if account_id:
            request.account = models.Account.objects.filter(pk=account_id).first()
            if request.account is None:
                request.session.flush()
        return self.get_response(request)


def account_context(request):
    account = getattr(request, 'account', None)
    unread = 0
    unread_concerns = unread_public = 0
    if account is not None and account.role != models.Account.ROLE_ADMIN:
        unread_concerns = models.StudentConcern.objects.filter(created_at__gt=account.last_seen_concerns).exclude(author=account).count() if account.last_seen_concerns else 0
        unread_public = models.ChatMessage.objects.filter(created_at__gt=account.last_seen_public_chat, deleted_at__isnull=True).exclude(account=account).count() if account.last_seen_public_chat else 0
        unread = models.PrivateMessage.objects.filter(
            recipient=account, read_at__isnull=True, deleted_at__isnull=True
        ).count()
    return {'account': account, 'unread_private': unread, 'unread_concerns': unread_concerns, 'unread_public': unread_public}


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.account is None:
                query = urlencode({'next': request.get_full_path()})
                return redirect(f"{reverse('login')}?{query}")
            if roles and request.account.role not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()[:64]
    return (request.META.get('REMOTE_ADDR') or '')[:64]


def log_activity(request, action, detail='', account=None, fullname='', role='', student_id=''):
    account = account or getattr(request, 'account', None)
    if account is not None:
        fullname = account.Fullname
        role = account.role
        student_id = '' if account.StudentID is None else str(account.StudentID)
    models.ActivityLog.objects.create(
        account=account,
        Fullname=fullname[:100],
        role=role,
        StudentID=student_id[:20],
        action=action,
        detail=detail[:300],
        ip=client_ip(request),
    )
