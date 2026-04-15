"""URL configuration for complaints app."""

from django.urls import path
from . import views, views_chatbot

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('citizen/', views.citizen_dashboard, name='citizen_dashboard'),
    path('authority/', views.authority_dashboard, name='authority_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/access-request/<int:profile_id>/approve/', views.approve_access_request, name='approve_access_request'),
    path('dashboard/admin/access-request/<int:profile_id>/reject/', views.reject_access_request, name='reject_access_request'),
    path('dashboard/admin/complaint/<int:id>/remind/', views.remind_assigned_authority, name='remind_assigned_authority'),
    path('complaint/<int:id>/', views.complaint_detail, name='complaint_detail'),
    path('complaint/<int:id>/acknowledge/', views.acknowledge_complaint, name='acknowledge_complaint'),
    path('complaint/<int:id>/request-resolution/', views.request_resolution_confirmation, name='request_resolution_confirmation'),
    path('complaint/<int:id>/confirm-resolution/', views.confirm_resolution, name='confirm_resolution'),
    path('complaint/<int:id>/reopen/', views.reopen_resolution, name='reopen_resolution'),
    path('complaint/<int:id>/document/<str:fmt>/', views.download_complaint_document, name='download_complaint_document'),
    
    # Chatbot URLs
    path('chatbot/', views_chatbot.chatbot_page, name='chatbot_page'),
    path('chatbot/session/create/', views_chatbot.create_chat_session, name='create_chat_session'),
    path('chatbot/session/<int:session_id>/', views_chatbot.get_chat_session, name='get_chat_session'),
    path('chatbot/session/<int:session_id>/message/', views_chatbot.send_message, name='send_message'),
    path('chatbot/session/<int:session_id>/close/', views_chatbot.close_chat_session, name='close_chat_session'),
]
