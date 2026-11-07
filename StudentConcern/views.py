import csv
import mimetypes
import os
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import CharField, Count, Q
from django.db.models.functions import Cast
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import models
from .access import log_activity, role_required
from .forms import (
    AccountForm, ConcernAdminForm, ConcernForm, LoginForm, ReplyForm, StatusForm,
)

Account = models.Account
ADMIN = Account.ROLE_ADMIN
STAFF = Account.ROLE_STAFF
STUDENT = Account.ROLE_STUDENT

ANON_NAME = 'Anonymous Participant'
ANON_COLLEGE = 'College of ***'
PAGE_SIZE = 10
LOG_PAGE_SIZE = 25


def build_qs(params, **overrides):
    data = {key: value for key, value in params.items() if value}
    for key, value in overrides.items():
        if value:
            data[key] = value
        else:
            data.pop(key, None)
    return '?' + urlencode(data) if data else '?'


def present(concern, viewer):
    full = viewer.role == ADMIN
    own = concern.owned_by(viewer)
    revealed = full or own
    concern.v_own = own
    concern.v_name = concern.Fullname if revealed else ANON_NAME
    if revealed:
        concern.v_id = '—' if concern.StudentID is None else concern.StudentID
    else:
        concern.v_id = 'Hidden'
    concern.v_college = concern.College if revealed or viewer.role == STAFF else ANON_COLLEGE
    return concern


def own_q(account):
    query = Q(author=account)
    if account.role == STUDENT and account.StudentID is not None:
        query |= Q(author__isnull=True, StudentID=account.StudentID, Fullname__iexact=account.Fullname)
    return query


def read_params(request, account):
    valid_colleges = [value for value, _ in models.StudentConcern.COLLEGE_CHOICES]
    valid_status = [value for value, _ in models.StudentConcern.STATUS_CHOICES]
    valid_category = [value for value, _ in models.StudentConcern.CATEGORY_CHOICES]
    college = request.GET.get('college', '').strip()
    if college not in valid_colleges or account.role == STUDENT:
        college = ''
    status = request.GET.get('status', '').strip()
    if status not in valid_status:
        status = ''
    category = request.GET.get('category', '').strip()
    if category not in valid_category:
        category = ''
    return {
        'q': ' '.join(request.GET.get('q', '').split())[:100],
        'college': college,
        'status': status,
        'category': category,
        'mine': '1' if request.GET.get('mine') == '1' else '',
    }


def apply_filters(queryset, params, account):
    if params['college']:
        queryset = queryset.filter(College=params['college'])
    if params['status']:
        queryset = queryset.filter(status=params['status'])
    if params['category']:
        queryset = queryset.filter(category=params['category'])
    if params['q']:
        queryset = queryset.annotate(student_id_text=Cast('StudentID', CharField()))
        for term in params['q'].split():
            cond = Q(Concern__icontains=term) | Q(category__icontains=term)
            if account.role == ADMIN:
                cond |= (
                    Q(Fullname__icontains=term)
                    | Q(student_id_text__startswith=term)
                    | Q(College__icontains=term)
                )
            else:
                cond |= own_q(account) & (
                    Q(Fullname__icontains=term) | Q(student_id_text__startswith=term)
                )
                if account.role == STAFF:
                    cond |= Q(College__icontains=term)
            queryset = queryset.filter(cond)
    return queryset


def describe_params(params):
    parts = []
    if params.get('mine'):
        parts.append('mine')
    if params['q']:
        parts.append(f'q="{params["q"]}"')
    for key in ('college', 'status', 'category'):
        if params[key]:
            parts.append(f'{key}="{params[key]}"')
    return ' '.join(parts)


def page_window(page, params):
    total = page.paginator.num_pages
    start = max(1, page.number - 2)
    end = min(total, page.number + 2)
    return [
        {'n': n, 'url': build_qs(params, page=n if n > 1 else None), 'current': n == page.number}
        for n in range(start, end + 1)
    ]


def listing(request):
    account = request.account
    account.last_seen_concerns = timezone.now()
    account.save(update_fields=['last_seen_concerns'])
    params = read_params(request, account)
    scoped = bool(params['mine'])
    base = models.StudentConcern.objects.all()
    if scoped:
        base = base.filter(own_q(account))
    concerns = apply_filters(base, params, account)

    show_colleges = account.role == ADMIN
    status_counts = dict(base.order_by().values_list('status').annotate(n=Count('id')))
    status_stats = [
        {
            'name': value,
            'count': status_counts.get(value, 0),
            'active': params['status'] == value,
            'url': build_qs(params, status=None if params['status'] == value else value),
        }
        for value, _ in models.StudentConcern.STATUS_CHOICES
    ]
    college_stats = []
    if show_colleges:
        counts = dict(base.order_by().values_list('College').annotate(n=Count('id')))
        college_stats = [
            {
                'name': name,
                'count': counts.get(value, 0),
                'active': params['college'] == value,
                'url': build_qs(params, college=value),
            }
            for value, name in models.StudentConcern.COLLEGE_CHOICES
        ]

    paginator = Paginator(concerns, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    rows = [present(c, account) for c in page.object_list]

    detail = describe_params(params)
    if params['q']:
        log_activity(request, 'search', detail)
    else:
        log_activity(request, 'view_dashboard', detail)

    return render(request, 'main.html', {
        'concerns': rows,
        'page': page,
        'paginator': paginator,
        'page_links': page_window(page, params),
        'prev_url': build_qs(params, page=page.previous_page_number()) if page.has_previous() else '',
        'next_url': build_qs(params, page=page.next_page_number()) if page.has_next() else '',
        'params': params,
        'query': params['q'],
        'selected_college': params['college'],
        'selected_status': params['status'],
        'selected_category': params['category'],
        'filtered': bool(params['q'] or params['college'] or params['status'] or params['category'] or params['mine']),
        'college_choices': models.StudentConcern.COLLEGE_CHOICES,
        'status_choices': models.StudentConcern.STATUS_CHOICES,
        'category_choices': models.StudentConcern.CATEGORY_CHOICES,
        'college_stats': college_stats,
        'status_stats': status_stats,
        'show_colleges': show_colleges,
        'college_filter': account.can_manage,
        'total': base.count(),
        'total_url': build_qs(params, college=None, status=None),
        'scoped': scoped,
        'clear_url': request.path,
        'export_url': build_qs(params) if params else '?',
    })


@role_required()
def StudentConcern(request):
    return listing(request)


def authenticate(data):
    role = data['role']
    name = data['Fullname']
    if role == ADMIN:
        if name == models.ADMIN_FULLNAME and data['StudentID'] == models.ADMIN_STUDENT_ID:
            account = Account.objects.filter(role=ADMIN).first()
            if account is None:
                account = Account.objects.create(
                    role=ADMIN, Fullname=models.ADMIN_FULLNAME, StudentID=models.ADMIN_STUDENT_ID
                )
            return account
        return None
    if role == STUDENT:
        return Account.objects.filter(
            role=STUDENT, StudentID=data['StudentID'], Fullname__iexact=name
        ).first()
    return Account.objects.filter(
        role=STAFF, College=data['College'], Fullname__iexact=name
    ).first()


def login_view(request):
    if request.account is not None:
        return redirect('StudentConcern')
    form = LoginForm(request.POST or None)
    mode = STUDENT
    if request.method == 'POST':
        posted = request.POST.get('role')
        if posted in (STUDENT, STAFF, ADMIN):
            mode = posted
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        account = authenticate(data)
        if account is not None:
            request.session.cycle_key()
            request.session['account_id'] = account.pk
            log_activity(request, 'login', f'Logged in as {account.get_role_display()}', account=account)
            messages.success(request, f'Welcome, {account.Fullname}.')
            target = request.POST.get('next') or request.GET.get('next') or ''
            if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
                return redirect(target)
            return redirect('StudentConcern')
        log_activity(
            request, 'login_failed', f'Attempted login as {data["role"]}',
            fullname=data['Fullname'], role=data['role'],
            student_id=str(data.get('StudentID') or ''),
        )
        form.add_error(None, 'No matching account found. Check your details and try again.')
    return render(request, 'login.html', {
        'form': form,
        'mode': mode,
        'next': request.GET.get('next', ''),
    })


@require_POST
def logout_view(request):
    if request.account is not None:
        log_activity(request, 'logout')
    request.session.flush()
    messages.success(request, 'You have been signed out.')
    return redirect('login')


@role_required()
def concern_detail(request, pk):
    request.account.last_seen_concerns = timezone.now()
    request.account.save(update_fields=['last_seen_concerns'])
    concern = get_object_or_404(models.StudentConcern, pk=pk)
    present(concern, request.account)
    log_activity(request, 'view_concern', f'Concern #{concern.pk}')
    context = {'concern': concern, 'replies': concern.replies.all()}
    if request.account.can_manage:
        context['status_form'] = StatusForm(instance=concern)
        context['reply_form'] = ReplyForm()
    return render(request, 'detail.html', context)


@role_required()
def concern_create(request):
    account = request.account
    form = ConcernForm(request.POST or None, request.FILES or None, with_college=account.role == ADMIN)
    if request.method == 'POST' and form.is_valid():
        concern = form.save(commit=False)
        concern.author = account
        concern.Fullname = account.Fullname
        concern.StudentID = account.StudentID
        if account.role != ADMIN:
            concern.College = account.College
        concern.save()
        log_activity(request, 'submit_concern', f'Concern #{concern.pk} ({concern.category})')
        messages.success(request, 'Concern submitted successfully.')
        return redirect('StudentConcern')
    return render(request, 'form.html', {
        'form': form, 'title': 'Submit a Concern',
        'subtitle': 'Describe what you need help with and attach an image as evidence if you have one.',
        'loading_text': 'Saving concern',
    })


@role_required(ADMIN)
def concern_update(request, pk):
    concern = get_object_or_404(models.StudentConcern, pk=pk)
    old_image = concern.evidence.name
    form = ConcernAdminForm(request.POST or None, request.FILES or None, instance=concern)
    if request.method == 'POST' and form.is_valid():
        storage = concern.evidence.storage
        form.save()
        if old_image and old_image != concern.evidence.name:
            storage.delete(old_image)
        log_activity(request, 'update_concern', f'Concern #{concern.pk}')
        messages.success(request, 'Concern updated successfully.')
        return redirect('StudentConcern')
    return render(request, 'form.html', {
        'form': form, 'title': 'Edit Concern',
        'subtitle': 'Update the details below, then save your changes.',
        'loading_text': 'Updating concern',
    })


@role_required(ADMIN)
def concern_delete(request, pk):
    concern = get_object_or_404(models.StudentConcern, pk=pk)
    if request.method == 'POST':
        number = concern.pk
        concern.delete()
        log_activity(request, 'delete_concern', f'Concern #{number}')
        messages.success(request, 'Concern deleted.')
        return redirect('StudentConcern')
    return render(request, 'confirm_delete.html', {'concern': concern})


@role_required(STAFF, ADMIN)
@require_POST
def concern_status(request, pk):
    concern = get_object_or_404(models.StudentConcern, pk=pk)
    old = concern.status
    form = StatusForm(request.POST, instance=concern)
    if form.is_valid():
        new = form.cleaned_data['status']
        if new != old:
            form.save()
            log_activity(request, 'change_status', f'Concern #{concern.pk}: {old} to {new}')
            messages.success(request, f'Status changed to {new}.')
        else:
            messages.success(request, 'Status is already set to that value.')
    else:
        messages.error(request, 'Select a valid status.')
    return redirect('concern_detail', pk=pk)


@role_required(STAFF, ADMIN)
@require_POST
def concern_reply(request, pk):
    concern = get_object_or_404(models.StudentConcern, pk=pk)
    form = ReplyForm(request.POST)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.concern = concern
        reply.author = request.account
        reply.author_name = request.account.Fullname
        reply.author_role = request.account.role
        reply.save()
        log_activity(request, 'reply', f'{reply.kind} on concern #{concern.pk}')
        messages.success(request, f'{reply.kind} posted.')
    else:
        messages.error(request, 'Write a message before posting.')
    return redirect('concern_detail', pk=pk)


def csv_safe(value):
    text = '' if value is None else str(value)
    if text[:1] in ('=', '+', '-', '@'):
        return "'" + text
    return text


@role_required(STAFF, ADMIN)
def export_csv(request):
    account = request.account
    params = read_params(request, account)
    base = models.StudentConcern.objects.all()
    if params['mine']:
        base = base.filter(own_q(account))
    concerns = apply_filters(base, params, account)
    stamp = timezone.localtime().strftime('%Y%m%d-%H%M')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="concerns-{stamp}.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Full Name', 'Student ID', 'College', 'Category', 'Priority',
        'Status', 'Concern', 'Submitted', 'Last Updated',
    ])
    count = 0
    for concern in concerns:
        present(concern, account)
        writer.writerow([
            concern.pk, csv_safe(concern.v_name), concern.v_id, concern.v_college,
            concern.category, concern.priority, concern.status, csv_safe(concern.Concern),
            timezone.localtime(concern.created_at).strftime('%Y-%m-%d %H:%M'),
            timezone.localtime(concern.updated_at).strftime('%Y-%m-%d %H:%M'),
        ])
        count += 1
    log_activity(request, 'export', f'{count} concern(s) {describe_params(params)}'.strip())
    return response


@role_required(ADMIN)
def accounts_list(request):
    query = ' '.join(request.GET.get('q', '').split())[:100]
    role = request.GET.get('role', '').strip()
    accounts = Account.objects.all()
    if role in (STUDENT, STAFF, ADMIN):
        accounts = accounts.filter(role=role)
    else:
        role = ''
    if query:
        accounts = accounts.annotate(student_id_text=Cast('StudentID', CharField()))
        for term in query.split():
            accounts = accounts.filter(
                Q(Fullname__icontains=term) | Q(College__icontains=term) | Q(student_id_text__startswith=term)
            )
    counts = dict(Account.objects.order_by().values_list('role').annotate(n=Count('id')))
    paginator = Paginator(accounts, PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    params = {'q': query, 'role': role}
    return render(request, 'accounts.html', {
        'accounts': page.object_list,
        'page': page,
        'paginator': paginator,
        'page_links': page_window(page, params),
        'prev_url': build_qs(params, page=page.previous_page_number()) if page.has_previous() else '',
        'next_url': build_qs(params, page=page.next_page_number()) if page.has_next() else '',
        'query': query,
        'selected_role': role,
        'role_choices': Account.ROLE_CHOICES,
        'filtered': bool(query or role),
        'counts': {
            'student': counts.get(STUDENT, 0),
            'staff': counts.get(STAFF, 0),
            'admin': counts.get(ADMIN, 0),
        },
        'total': Account.objects.count(),
    })


@role_required(ADMIN)
def account_create(request):
    form = AccountForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        account = form.save()
        log_activity(request, 'create_account', f'{account.get_role_display()}: {account.Fullname}')
        messages.success(request, f'{account.get_role_display()} account registered.')
        return redirect('accounts_list')
    return render(request, 'form.html', {
        'form': form, 'title': 'Register Account',
        'subtitle': 'Create a student or staff account so they can log in.',
        'eyebrow': 'Account form', 'loading_text': 'Saving account',
        'cancel_url': reverse('accounts_list'), 'account_form': True,
    })


@role_required(ADMIN)
def account_update(request, pk):
    target = get_object_or_404(Account, pk=pk, role__in=(STUDENT, STAFF))
    form = AccountForm(request.POST or None, instance=target)
    if request.method == 'POST' and form.is_valid():
        target = form.save()
        models.StudentConcern.objects.filter(author=target).update(
            Fullname=target.Fullname, StudentID=target.StudentID,
            College=target.College or models.StudentConcern.COLLEGE_CHOICES[0][0],
        )
        log_activity(request, 'update_account', f'{target.get_role_display()}: {target.Fullname}')
        messages.success(request, 'Account updated successfully.')
        return redirect('accounts_list')
    return render(request, 'form.html', {
        'form': form, 'title': 'Edit Account',
        'subtitle': 'Update the account details, then save your changes.',
        'eyebrow': 'Account form', 'loading_text': 'Updating account',
        'cancel_url': reverse('accounts_list'), 'account_form': True,
    })


@role_required(ADMIN)
def account_delete(request, pk):
    target = get_object_or_404(Account, pk=pk, role__in=(STUDENT, STAFF))
    if request.method == 'POST':
        label = f'{target.get_role_display()}: {target.Fullname}'
        target.delete()
        log_activity(request, 'delete_account', label)
        messages.success(request, 'Account deleted.')
        return redirect('accounts_list')
    return render(request, 'account_confirm_delete.html', {'target': target})


def filtered_logs(request):
    logs = models.ActivityLog.objects.all()
    query = ' '.join(request.GET.get('q', '').split())[:100]
    role = request.GET.get('role', '').strip()
    action = request.GET.get('action', '').strip()
    if role in (STUDENT, STAFF, ADMIN):
        logs = logs.filter(role=role)
    else:
        role = ''
    if action in [value for value, _ in models.ActivityLog.ACTION_CHOICES]:
        logs = logs.filter(action=action)
    else:
        action = ''
    for term in query.split():
        logs = logs.filter(
            Q(Fullname__icontains=term) | Q(StudentID__startswith=term)
            | Q(detail__icontains=term) | Q(ip__icontains=term)
        )
    return logs, {'q': query, 'role': role, 'action': action}


@role_required(ADMIN)
def activity_logs(request):
    logs, params = filtered_logs(request)
    paginator = Paginator(logs, LOG_PAGE_SIZE)
    page = paginator.get_page(request.GET.get('page'))
    rows = list(page.object_list)
    last = logs.order_by('-id').values_list('id', flat=True).first() or 0
    return render(request, 'logs.html', {
        'logs': rows,
        'page': page,
        'paginator': paginator,
        'page_links': page_window(page, params),
        'prev_url': build_qs(params, page=page.previous_page_number()) if page.has_previous() else '',
        'next_url': build_qs(params, page=page.next_page_number()) if page.has_next() else '',
        'params': params,
        'query': params['q'],
        'selected_role': params['role'],
        'selected_action': params['action'],
        'role_choices': Account.ROLE_CHOICES,
        'action_choices': models.ActivityLog.ACTION_CHOICES,
        'filtered': bool(params['q'] or params['role'] or params['action']),
        'live': page.number == 1,
        'last_id': last,
        'feed_qs': build_qs(params),
        'total': models.ActivityLog.objects.count(),
    })


@role_required(ADMIN)
def activity_feed(request):
    logs, _ = filtered_logs(request)
    try:
        after = int(request.GET.get('after', 0))
    except ValueError:
        after = 0
    fresh = list(logs.filter(id__gt=after).order_by('id')[:50])
    rows = [
        {
            'id': item.id,
            'time': timezone.localtime(item.created_at).strftime('%b %d, %Y %I:%M:%S %p'),
            'student_id': item.StudentID or '—',
            'name': item.Fullname or '—',
            'role': item.role.title() or '—',
            'action': item.get_action_display(),
            'detail': item.detail or '—',
            'ip': item.ip or '—',
        }
        for item in fresh
    ]
    return JsonResponse({'rows': rows, 'last_id': fresh[-1].id if fresh else after})


CHAT_PAGE = 50
CHAT_MAX_LENGTH = 500
CHAT_BURST = 5
CHAT_BURST_SECONDS = 10
PEOPLE_ROLES = (STUDENT, STAFF)


def handle(account):
    if account.role == STUDENT:
        return f'ID {account.StudentID}'
    return account.Fullname


def payload(message, viewer, name, role, sender_id):
    own = sender_id is not None and sender_id == viewer.id
    admin = viewer.role == ADMIN
    editable = own and message.within_window
    return {
        'id': message.id,
        'name': name,
        'role': role,
        'role_label': role.title(),
        'text': message.message,
        'time': timezone.localtime(message.created_at).strftime('%b %d, %I:%M %p'),
        'own': own,
        'edited': message.edited,
        'can_edit': editable,
        'can_delete': editable or admin,
        'admin_delete': admin,
        'can_reply': role != ADMIN and not admin,
        'seconds_left': message.seconds_left if editable else 0,
        'reply': ({'id': message.reply_to_id, 'text': message.reply_to.message[:15], 'name': (getattr(message.reply_to, 'author_name', '') or (handle(message.reply_to.sender) if hasattr(message.reply_to, 'sender_id') else ''))} if message.reply_to_id and message.reply_to.deleted_at is None else None),
        'reactions': list(message.reactions.values('reaction').annotate(count=Count('id')).order_by('reaction')),
        'attachment_url': reverse('chat_attachment', kwargs={'kind': 'public' if hasattr(message, 'account_id') else 'private', 'pk': message.pk}) if message.attachment else '',
        'attachment_name': message.attachment_name,
        'attachment_type': message.attachment_type,
    }


def public_payload(message, viewer):
    return payload(message, viewer, message.author_name, message.author_role, message.account_id)


def private_payload(message, viewer):
    data = payload(message, viewer, message.sender.Fullname, message.sender.role, message.sender_id)
    data['student_id'] = message.sender.StudentID
    return data


def clean_text(request):
    return request.POST.get('message', '').strip()[:CHAT_MAX_LENGTH]


def is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def flood_error(queryset):
    since = timezone.now() - timedelta(seconds=CHAT_BURST_SECONDS)
    if queryset.filter(created_at__gte=since).count() >= CHAT_BURST:
        return 'You are sending messages too fast. Wait a few seconds.'
    return ''


def fail(request, error, redirect_to, status=400):
    if is_ajax(request) or status >= 403:
        return JsonResponse({'ok': False, 'error': error}, status=status)
    messages.error(request, error)
    return redirect(redirect_to)


def feed_response(request, new_qs, changed_qs, build):
    try:
        after = int(request.GET.get('after', 0))
    except ValueError:
        after = 0
    try:
        since = datetime.fromtimestamp(float(request.GET.get('since', '')), tz=dt_timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        since = timezone.now() - timedelta(seconds=5)
    fresh = list(new_qs.filter(id__gt=after, deleted_at__isnull=True).order_by('id')[:100])
    changed = []
    for item in changed_qs.filter(id__lte=after, updated_at__gt=since).order_by('id')[:100]:
        if item.deleted_at is not None:
            changed.append({'id': item.id, 'deleted': True})
        else:
            changed.append(build(item, request.account))
    rows = [build(item, request.account) for item in fresh]
    return JsonResponse({
        'messages': rows,
        'changed': changed,
        'last_id': rows[-1]['id'] if rows else after,
        'now': timezone.now().timestamp() - 2,
    })


@role_required()
def chat_room(request):
    request.account.last_seen_public_chat = timezone.now()
    request.account.save(update_fields=['last_seen_public_chat'])
    recent = models.ChatMessage.objects.filter(deleted_at__isnull=True).order_by('-id')[:CHAT_PAGE]
    rows = [public_payload(m, request.account) for m in reversed(list(recent))]
    return render(request, 'chat.html', {
        'messages_list': rows,
        'last_id': rows[-1]['id'] if rows else 0,
        'since': timezone.now().timestamp() - 2,
        'max_length': CHAT_MAX_LENGTH,
        'feed_url': reverse('chat_feed'),
        'send_url': reverse('chat_send'),
        'edit_url': reverse('chat_edit', args=[0]),
        'delete_url': reverse('chat_delete', args=[0]),
        'reaction_url': reverse('chat_reaction', args=[0]),
        'placeholder': 'Message everyone',
    })


CHAT_UPLOAD_MAX = 20 * 1024 * 1024


def read_chat_upload(request):
    upload = request.FILES.get('attachment')
    if not upload:
        return None, '', '', ''
    if upload.size > CHAT_UPLOAD_MAX:
        return False, '', '', 'Files must be 20 MB or smaller.'
    content_type = (upload.content_type or '').lower()
    if content_type.startswith('image/'):
        kind = 'image'
    elif content_type.startswith('audio/'):
        kind = 'audio'
    else:
        kind = 'file'
    # Permit common browser-recorder formats even if the browser sends a generic MIME type.
    ext = os.path.splitext(upload.name)[1].lower()
    if ext in ('.webm', '.wav', '.mp3', '.m4a', '.ogg', '.mp4', '.aac'):
        kind = 'audio'
    return upload, upload.name[:255], kind, ''


@role_required()
@require_POST
def chat_send(request):
    text = clean_text(request)
    upload, upload_name, upload_kind, upload_error = read_chat_upload(request)
    if upload is False:
        return fail(request, upload_error, 'chat_room')
    if not text and not upload:
        return fail(request, 'Write a message or attach a file first.', 'chat_room')
    error = flood_error(models.ChatMessage.objects.filter(account=request.account))
    if error:
        return fail(request, error, 'chat_room')
    reply_to = None
    reply_id = request.POST.get('reply_to')
    if reply_id and request.account.role == ADMIN:
        return fail(request, 'Admin accounts cannot reply to messages.', 'chat_room', 403)
    if reply_id:
        reply_to = get_object_or_404(models.ChatMessage, pk=reply_id, deleted_at__isnull=True)
        if reply_to.author_role == ADMIN:
            return fail(request, 'Admin messages cannot be replied to.', 'chat_room', 403)
    message = models.ChatMessage.objects.create(
        reply_to=reply_to, account=request.account,
        author_name=request.account.Fullname,
        author_role=request.account.role,
        message=text,
        attachment=upload if upload else None,
        attachment_name=upload_name,
        attachment_type=upload_kind,
    )
    log_activity(request, 'chat_message', text[:150])
    if is_ajax(request):
        return JsonResponse({'ok': True, 'message': public_payload(message, request.account)})
    return redirect('chat_room')


@role_required()
def chat_mention_accounts(request):
    """Return registered accounts for Public Chat @-mention autocomplete."""
    query = (request.GET.get('q') or '').strip()[:100]
    accounts = Account.objects.all().order_by('Fullname', 'id')
    if query:
        accounts = accounts.filter(Fullname__istartswith=query)
    return JsonResponse({
        'accounts': [
            {'id': account.pk, 'name': account.Fullname, 'role': account.get_role_display()}
            for account in accounts
        ]
    })


@role_required()
def chat_feed(request):
    return feed_response(request, models.ChatMessage.objects.all(), models.ChatMessage.objects.all(), public_payload)


@role_required()
def chat_attachment(request, kind, pk):
    if kind == 'public':
        message = get_object_or_404(models.ChatMessage, pk=pk, deleted_at__isnull=True)
    elif kind == 'private':
        message = get_object_or_404(models.PrivateMessage, pk=pk, deleted_at__isnull=True)
        if request.account.id not in (message.sender_id, message.recipient_id):
            return HttpResponse('Forbidden', status=403)
    else:
        return HttpResponse('Not found', status=404)
    if not message.attachment:
        return HttpResponse('Not found', status=404)
    mime_type = mimetypes.guess_type(message.attachment_name or message.attachment.name)[0] or 'application/octet-stream'
    response = FileResponse(message.attachment.open('rb'), content_type=mime_type)
    safe_name = ''.join(ch for ch in (message.attachment_name or 'download') if ch.isalnum() or ch in ' ._-') or 'download'
    if message.attachment_type in ('image', 'audio'):
        response['Content-Disposition'] = 'inline; filename="%s"' % safe_name
    else:
        response['Content-Disposition'] = 'attachment; filename="%s"' % safe_name
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@role_required()
@require_POST
def chat_edit(request, pk):
    message = get_object_or_404(models.ChatMessage, pk=pk, deleted_at__isnull=True)
    if message.account_id != request.account.id:
        return fail(request, 'You can only edit your own messages.', 'chat_room', 403)
    if not message.within_window:
        return fail(request, 'The 30-second edit window has closed.', 'chat_room', 403)
    text = clean_text(request)
    if not text:
        return fail(request, 'Message cannot be empty.', 'chat_room')
    message.mark_edited(text)
    log_activity(request, 'chat_edit', f'#{message.pk}: {text[:150]}')
    return JsonResponse({'ok': True, 'message': public_payload(message, request.account)})


@role_required()
@require_POST
def chat_delete(request, pk):
    message = get_object_or_404(models.ChatMessage, pk=pk, deleted_at__isnull=True)
    own = message.account_id == request.account.id
    if not (request.account.role == ADMIN or (own and message.within_window)):
        return fail(request, 'You can no longer delete this message.', 'chat_room', 403)
    detail = f'#{message.pk} {message.author_name}: {message.message[:120]}'
    message.mark_deleted()
    log_activity(request, 'chat_delete', detail)
    if is_ajax(request):
        return JsonResponse({'ok': True})
    return redirect('chat_room')


@role_required()
@require_POST
def chat_reaction(request, pk):
    message = get_object_or_404(models.ChatMessage, pk=pk, deleted_at__isnull=True)
    return save_chat_reaction(request, message=message)


@role_required(*PEOPLE_ROLES)
@require_POST
def private_reaction(request, pk):
    message = get_object_or_404(models.PrivateMessage, pk=pk, deleted_at__isnull=True)
    if request.account.id not in (message.sender_id, message.recipient_id):
        return JsonResponse({'ok': False, 'error': 'This message is not part of your conversation.'}, status=403)
    return save_chat_reaction(request, private_message=message)


def save_chat_reaction(request, message=None, private_message=None):
    allowed = {value for value, _label in models.ChatReaction.REACTION_CHOICES}
    reaction = request.POST.get('reaction', '')
    if reaction not in allowed:
        return JsonResponse({'ok': False, 'error': 'Unsupported reaction.'}, status=400)
    lookup = {'message': message, 'private_message': private_message, 'account': request.account}
    existing = models.ChatReaction.objects.filter(**lookup).first()
    if existing and existing.reaction == reaction:
        existing.delete()
        active = False
    else:
        models.ChatReaction.objects.update_or_create(**lookup, defaults={'reaction': reaction})
        active = True
    target = message or private_message
    target.updated_at = timezone.now()
    target.save(update_fields=['updated_at'])
    qs = models.ChatReaction.objects.filter(message=message) if message else models.ChatReaction.objects.filter(private_message=private_message)
    counts = list(qs.values('reaction').annotate(count=Count('id')).order_by('reaction'))
    return JsonResponse({'ok': True, 'active': active, 'reactions': counts})


def pair_messages(account, other):
    return models.PrivateMessage.objects.filter(
        Q(sender=account, recipient=other) | Q(sender=other, recipient=account)
    )


def conversations(account):
    threads = {}
    recent = models.PrivateMessage.objects.filter(
        Q(sender=account) | Q(recipient=account), deleted_at__isnull=True
    ).select_related('sender', 'recipient').order_by('-id')[:500]
    for item in recent:
        other = item.recipient if item.sender_id == account.id else item.sender
        entry = threads.setdefault(other.id, {
            'account': other, 'last': item, 'unread': 0,
        })
        if item.recipient_id == account.id and item.read_at is None:
            entry['unread'] += 1
    rows = []
    for entry in threads.values():
        other = entry['account']
        last = entry['last']
        rows.append({
            'id': other.id,
            'handle': handle(other),
            'fullname': other.Fullname,
            'student_id': other.StudentID,
            'nickname': models.ConversationNickname.objects.filter(owner=account, partner=other).values_list('nickname', flat=True).first() or '',
            'online': bool(other.last_active_at and other.last_active_at >= timezone.now() - timedelta(seconds=75)),
            'role': other.role,
            'role_label': other.role.title(),
            'preview': ('You: ' if last.sender_id == account.id else '') + last.message[:40],
            'unread': entry['unread'],
        })
    return rows


def search_people(account, query):
    people = Account.objects.filter(role__in=PEOPLE_ROLES).exclude(pk=account.pk)
    people = people.annotate(student_id_text=Cast('StudentID', CharField()))
    for term in query.split():
        people = people.filter(Q(Fullname__icontains=term) | Q(student_id_text__startswith=term))
    return [
        {'id': a.id, 'handle': handle(a), 'role': a.role, 'role_label': a.role.title()}
        for a in people.order_by('role', 'Fullname')[:30]
    ]


def private_context(request, partner=None):
    account = request.account
    account.last_active_at = timezone.now()
    account.save(update_fields=['last_active_at'])
    query = ' '.join(request.GET.get('q', '').split())[:100]
    context = {
        'query': query,
        'results': search_people(account, query) if query else None,
        'threads': conversations(account),
        'partner': partner,
    }
    if partner is not None:
        pair = pair_messages(account, partner).filter(deleted_at__isnull=True).select_related('sender')
        recent = list(pair.order_by('-id')[:CHAT_PAGE])[::-1]
        pair.filter(recipient=account, read_at__isnull=True).update(read_at=timezone.now())
        rows = [private_payload(m, account) for m in recent]
        nickname = models.ConversationNickname.objects.filter(owner=account, partner=partner).values_list('nickname', flat=True).first() or ''
        listed = False
        for thread in context['threads']:
            if thread['id'] == partner.id:
                thread['unread'] = 0
                listed = True
        if not listed:
            context['threads'].insert(0, {
                'id': partner.id,
                'handle': handle(partner),
                'fullname': partner.Fullname,
                'student_id': partner.StudentID,
                'nickname': nickname,
                'online': bool(partner.last_active_at and partner.last_active_at >= timezone.now() - timedelta(seconds=75)),
                'role': partner.role,
                'role_label': partner.role.title(),
                'preview': 'New conversation',
                'unread': 0,
            })
        context.update({
            'partner_handle': handle(partner),
            'partner_fullname': partner.Fullname,
            'partner_student_id': partner.StudentID,
            'partner_nickname': nickname,
            'partner_online': bool(partner.last_active_at and partner.last_active_at >= timezone.now() - timedelta(seconds=75)),
            'nickname_url': reverse('private_nickname', args=[partner.pk]),
            'presence_url': reverse('private_presence', args=[partner.pk]),
            'messages_list': rows,
            'last_id': rows[-1]['id'] if rows else 0,
            'since': timezone.now().timestamp() - 2,
            'max_length': CHAT_MAX_LENGTH,
            'feed_url': reverse('private_feed', args=[partner.pk]),
            'send_url': reverse('private_send', args=[partner.pk]),
            'edit_url': reverse('private_edit', args=[0]),
            'delete_url': reverse('private_delete', args=[0]),
        'reaction_url': reverse('private_reaction', args=[0]),
            'placeholder': f'Message {handle(partner)}',
        })
    return context


@role_required(*PEOPLE_ROLES)
def private_chat(request):
    return render(request, 'private.html', private_context(request))


@role_required(*PEOPLE_ROLES)
def private_thread(request, pk):
    if pk == request.account.pk:
        return redirect('private_chat')
    partner = get_object_or_404(Account, pk=pk, role__in=PEOPLE_ROLES)
    return render(request, 'private.html', private_context(request, partner))


@role_required(*PEOPLE_ROLES)
@require_POST
def private_send(request, pk):
    partner = get_object_or_404(Account, pk=pk, role__in=PEOPLE_ROLES)
    back = reverse('private_thread', args=[partner.pk])
    if partner.pk == request.account.pk:
        return fail(request, 'You cannot message yourself.', 'private_chat')
    text = clean_text(request)
    upload, upload_name, upload_kind, upload_error = read_chat_upload(request)
    if upload is False:
        return fail(request, upload_error, back)
    if not text and not upload:
        return fail(request, 'Write a message or attach a file first.', back)
    error = flood_error(models.PrivateMessage.objects.filter(sender=request.account))
    if error:
        return fail(request, error, back)
    reply_to = None
    reply_id = request.POST.get('reply_to')
    if reply_id:
        reply_to = get_object_or_404(pair_messages(request.account, partner), pk=reply_id, deleted_at__isnull=True)
    message = models.PrivateMessage.objects.create(
        sender=request.account, recipient=partner, reply_to=reply_to, message=text,
        attachment=upload if upload else None, attachment_name=upload_name, attachment_type=upload_kind,
    )
    log_activity(request, 'private_message', f'To {handle(partner)}')
    if is_ajax(request):
        return JsonResponse({'ok': True, 'message': private_payload(message, request.account)})
    return redirect(back)


@role_required(*PEOPLE_ROLES)
def private_feed(request, pk):
    partner = get_object_or_404(Account, pk=pk, role__in=PEOPLE_ROLES)
    pair = pair_messages(request.account, partner).select_related('sender')
    pair.filter(recipient=request.account, read_at__isnull=True).update(read_at=timezone.now())
    return feed_response(request, pair, pair, private_payload)


@role_required(*PEOPLE_ROLES)
@require_POST
def private_edit(request, pk):
    message = get_object_or_404(models.PrivateMessage, pk=pk, deleted_at__isnull=True)
    if message.sender_id != request.account.id:
        return fail(request, 'You can only edit your own messages.', 'private_chat', 403)
    if not message.within_window:
        return fail(request, 'The 30-second edit window has closed.', 'private_chat', 403)
    text = clean_text(request)
    if not text:
        return fail(request, 'Message cannot be empty.', 'private_chat')
    message.mark_edited(text)
    log_activity(request, 'private_edit', f'To {handle(message.recipient)}')
    return JsonResponse({'ok': True, 'message': private_payload(message, request.account)})


@role_required(*PEOPLE_ROLES)
@require_POST
def private_delete(request, pk):
    message = get_object_or_404(models.PrivateMessage, pk=pk, deleted_at__isnull=True)
    if message.sender_id != request.account.id or not message.within_window:
        return fail(request, 'You can no longer delete this message.', 'private_chat', 403)
    recipient = message.recipient
    message.mark_deleted()
    log_activity(request, 'private_delete', f'To {handle(recipient)}')
    return JsonResponse({'ok': True})


@role_required(*PEOPLE_ROLES)
@require_POST
def presence_heartbeat(request):
    request.account.last_active_at = timezone.now()
    request.account.save(update_fields=['last_active_at'])
    return JsonResponse({'ok': True})


@role_required(*PEOPLE_ROLES)
@require_POST
def private_nickname(request, pk):
    partner = get_object_or_404(Account, pk=pk, role__in=PEOPLE_ROLES)
    if partner.pk == request.account.pk:
        return JsonResponse({'ok': False}, status=400)
    nickname = ' '.join(request.POST.get('nickname', '').split())[:60]
    if nickname:
        models.ConversationNickname.objects.update_or_create(owner=request.account, partner=partner, defaults={'nickname': nickname})
    else:
        models.ConversationNickname.objects.filter(owner=request.account, partner=partner).delete()
    return JsonResponse({'ok': True, 'nickname': nickname})


@role_required(*PEOPLE_ROLES)
def private_presence(request, pk):
    partner = get_object_or_404(Account, pk=pk, role__in=PEOPLE_ROLES)
    if partner.pk == request.account.pk:
        return JsonResponse({'online': False})
    request.account.last_active_at = timezone.now()
    request.account.save(update_fields=['last_active_at'])
    online = bool(partner.last_active_at and partner.last_active_at >= timezone.now() - timedelta(seconds=75))
    return JsonResponse({'online': online})


@role_required()
def notification_counts(request):
    account = request.account
    concerns = models.StudentConcern.objects.filter(created_at__gt=account.last_seen_concerns or timezone.make_aware(datetime(2000,1,1))).exclude(author=account).count()
    public = models.ChatMessage.objects.filter(created_at__gt=account.last_seen_public_chat or timezone.make_aware(datetime(2000,1,1)), deleted_at__isnull=True).exclude(account=account).count()
    private = models.PrivateMessage.objects.filter(recipient=account, read_at__isnull=True, deleted_at__isnull=True).count()
    return JsonResponse({'concerns': concerns, 'public': public, 'private': private})
