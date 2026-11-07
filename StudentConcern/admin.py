from django.contrib import admin

from .models import Account, ActivityLog, ChatMessage, ConcernReply, StudentConcern


@admin.register(StudentConcern)
class StudentConcernAdmin(admin.ModelAdmin):
    list_display = ('Fullname', 'StudentID', 'College', 'category', 'priority', 'status', 'Concern')
    list_filter = ('status', 'category', 'priority', 'College')
    search_fields = ('Fullname', 'College', 'Concern')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('Fullname', 'role', 'StudentID', 'College', 'created_at')
    list_filter = ('role', 'College')
    search_fields = ('Fullname', 'College')


@admin.register(ConcernReply)
class ConcernReplyAdmin(admin.ModelAdmin):
    list_display = ('concern', 'kind', 'author_name', 'created_at')
    list_filter = ('kind',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'StudentID', 'Fullname', 'role', 'action', 'detail', 'ip')
    list_filter = ('role', 'action')
    search_fields = ('Fullname', 'StudentID', 'detail')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'author_name', 'author_role', 'message')
    list_filter = ('author_role',)
    search_fields = ('author_name', 'message')
