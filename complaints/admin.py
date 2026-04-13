from django.contrib import admin
from .models import UserProfile, Complaint, ComplaintUpdate, ChatSession, ChatMessage, ExtractedComplaint


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'thana', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__email', 'thana')


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('id', 'citizen', 'category', 'thana', 'status', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('description', 'area', 'citizen__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ComplaintUpdate)
class ComplaintUpdateAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'updated_by', 'status_change', 'created_at')
    list_filter = ('status_change', 'created_at')
    search_fields = ('message', 'complaint__id')


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


@admin.register(ExtractedComplaint)
class ExtractedComplaintAdmin(admin.ModelAdmin):
    list_display = ('category', 'area_thana', 'inconsistency_score', 'extracted_at')
    list_filter = ('category', 'inconsistency_score', 'extracted_at')
    search_fields = ('category', 'area_thana', 'keywords')
    readonly_fields = ('extracted_at',)

