from django.contrib import admin
from .models import (
    ChatAttachment,
    ChatMessage,
    ChatSession,
    Complaint,
    ComplaintActivity,
    ComplaintUpdate,
    ExtractedComplaint,
    UserProfile,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'approval_status', 'thana', 'department', 'created_at')
    list_filter = ('role', 'approval_status', 'created_at')
    search_fields = ('user__email', 'thana', 'department', 'employee_id')


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('id', 'citizen', 'category', 'thana', 'status', 'assigned_authority', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('description', 'area', 'citizen__email')
    readonly_fields = (
        'created_at',
        'updated_at',
        'acknowledged_at',
        'resolution_requested_at',
        'citizen_confirmed_at',
        'resolved_at',
        'last_reminder_sent_at',
        'email_sent_at',
    )


@admin.register(ComplaintUpdate)
class ComplaintUpdateAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'updated_by', 'status_change', 'created_at')
    list_filter = ('status_change', 'created_at')
    search_fields = ('message', 'complaint__id')


@admin.register(ComplaintActivity)
class ComplaintActivityAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'event_type', 'actor', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('complaint__id', 'message', 'actor__email')
    readonly_fields = ('created_at',)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'language', 'is_active', 'created_at')
    list_filter = ('language', 'is_active', 'created_at')
    search_fields = ('title', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('chat_session', 'role', 'content', 'timestamp')
    list_filter = ('role', 'timestamp')
    search_fields = ('content', 'chat_session__title')
    readonly_fields = ('timestamp',)


@admin.register(ChatAttachment)
class ChatAttachmentAdmin(admin.ModelAdmin):
    list_display = ('message', 'original_name', 'content_type', 'uploaded_at')
    list_filter = ('content_type', 'uploaded_at')
    search_fields = ('original_name', 'message__content')
    readonly_fields = ('uploaded_at',)


@admin.register(ExtractedComplaint)
class ExtractedComplaintAdmin(admin.ModelAdmin):
    list_display = ('category', 'area_thana', 'inconsistency_score', 'extracted_at')
    list_filter = ('category', 'inconsistency_score', 'extracted_at')
    search_fields = ('category', 'area_thana', 'keywords')
    readonly_fields = ('extracted_at',)

