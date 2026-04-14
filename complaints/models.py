"""Django models for the complaints system."""

import os

from django.db import models
from django.contrib.auth.models import User


def chat_attachment_upload_to(instance, filename):
    """Store chat images under a predictable media path."""
    return os.path.join('chat_attachments', str(instance.message.chat_session_id), filename)


class UserProfile(models.Model):
    """Extended user profile with role and location."""
    
    ROLE_CHOICES = [
        ('citizen', 'Citizen'),
        ('authority', 'Authority'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='citizen')
    thana = models.CharField(max_length=100, blank=True, null=True)  # For authority users
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.role}"


class Complaint(models.Model):
    """Model for citizen complaints."""
    
    CATEGORY_CHOICES = [
        ('environment', 'Environment'),
        ('health', 'Health'),
        ('water', 'Water'),
        ('electricity', 'Electricity'),
        ('roads', 'Roads'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    citizen = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    thana = models.CharField(max_length=100)
    area = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    assigned_authority = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_complaints',
        limit_choices_to={'userprofile__role': 'authority'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    generated_docx_path = models.CharField(max_length=500, blank=True)
    generated_pdf_path = models.CharField(max_length=500, blank=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_error = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Complaint #{self.id} - {self.category} ({self.status})"


class ComplaintUpdate(models.Model):
    """Updates/responses to complaints."""
    
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='updates')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    message = models.TextField()
    status_change = models.CharField(
        max_length=20,
        choices=Complaint.STATUS_CHOICES,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Update to Complaint #{self.complaint.id}"


class ChatSession(models.Model):
    """Chat session for complaint-related conversations."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    generated_complaint = models.ForeignKey(
        'Complaint',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_chat_sessions',
    )
    title = models.CharField(max_length=200, default="New Complaint Chat")
    language = models.CharField(
        max_length=10,
        choices=[('en', 'English'), ('bn', 'Bangla')],
        default='en'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Chat Session: {self.title} ({self.user.email})"


class ChatMessage(models.Model):
    """Individual messages in a chat session."""
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class ChatAttachment(models.Model):
    """Uploaded media attached to a chat message."""

    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=chat_attachment_upload_to)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Attachment for message #{self.message_id}: {self.original_name}"


class ExtractedComplaint(models.Model):
    """Extracted complaint information from chat."""
    
    chat_session = models.OneToOneField(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='extracted_complaint'
    )
    category = models.CharField(max_length=100, blank=True)
    area_thana = models.CharField(max_length=100, blank=True)  # Area/Thana in Dhaka
    duration = models.CharField(max_length=100, blank=True)  # How long the issue exists
    keywords = models.JSONField(default=list, blank=True)  # List of extracted keywords
    inconsistency_score = models.IntegerField(default=3)  # 1-5 scale, 1=consistent, 5=inconsistent
    policy_reference = models.CharField(max_length=200, blank=True)  # Relevant policy
    web_search_results = models.JSONField(default=list, blank=True)  # Results from web search
    full_description = models.TextField(blank=True)
    extracted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Extracted: {self.category} - {self.area_thana}"

