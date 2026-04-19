"""URL configuration for complaints app."""

from django.urls import path
from . import views, views_api, views_chatbot, views_native_api

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

    # API auth endpoints for Next.js frontend
    path('api/auth/signup/', views_api.api_signup, name='api_signup'),
    path('api/auth/login/', views_api.api_login, name='api_login'),
    path('api/auth/logout/', views_api.api_logout, name='api_logout'),
    path('api/auth/me/', views_api.api_me, name='api_me'),
    path('api/auth/session/', views_api.api_session_login, name='api_session_login'),
    path('api/auth/session/logout/', views_api.api_session_logout, name='api_session_logout'),

    # API chatbot endpoints
    path('api/chatbot/sessions/', views_chatbot.list_chat_sessions, name='api_list_chat_sessions'),
    path('api/chatbot/session/create/', views_chatbot.create_chat_session, name='api_create_chat_session'),
    path('api/chatbot/session/<int:session_id>/', views_chatbot.get_chat_session, name='api_get_chat_session'),
    path('api/chatbot/session/<int:session_id>/message/', views_chatbot.send_message, name='api_send_message'),
    path('api/chatbot/session/<int:session_id>/close/', views_chatbot.close_chat_session, name='api_close_chat_session'),

    # Native dashboard APIs
    path('api/dashboard/citizen/', views_native_api.api_citizen_dashboard, name='api_citizen_dashboard'),
    path('api/dashboard/citizen/complaints/', views_native_api.api_citizen_create_complaint, name='api_citizen_create_complaint'),
    path('api/dashboard/authority/', views_native_api.api_authority_dashboard, name='api_authority_dashboard'),
    path('api/dashboard/admin/', views_native_api.api_admin_dashboard, name='api_admin_dashboard'),
    path('api/dashboard/admin/access-request/<int:profile_id>/approve/', views_native_api.api_admin_approve_access_request, name='api_admin_approve_access_request'),
    path('api/dashboard/admin/access-request/<int:profile_id>/reject/', views_native_api.api_admin_reject_access_request, name='api_admin_reject_access_request'),
    path('api/dashboard/admin/complaint/<int:id>/remind/', views_native_api.api_admin_remind_assigned_authority, name='api_admin_remind_assigned_authority'),

    # Native complaint lifecycle/detail APIs
    path('api/complaints/<int:id>/', views_native_api.api_complaint_detail, name='api_complaint_detail'),
    path('api/complaints/<int:id>/notes/', views_native_api.api_complaint_add_note, name='api_complaint_add_note'),
    path('api/complaints/<int:id>/acknowledge/', views_native_api.api_complaint_acknowledge, name='api_complaint_acknowledge'),
    path('api/complaints/<int:id>/request-resolution/', views_native_api.api_complaint_request_resolution, name='api_complaint_request_resolution'),
    path('api/complaints/<int:id>/confirm-resolution/', views_native_api.api_complaint_confirm_resolution, name='api_complaint_confirm_resolution'),
    path('api/complaints/<int:id>/reopen/', views_native_api.api_complaint_reopen, name='api_complaint_reopen'),
]
