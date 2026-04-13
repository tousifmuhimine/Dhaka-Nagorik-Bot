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
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('complaint/<int:id>/', views.complaint_detail, name='complaint_detail'),
    
    # Chatbot URLs
    path('chatbot/', views_chatbot.chatbot_page, name='chatbot_page'),
    path('chatbot/session/create/', views_chatbot.create_chat_session, name='create_chat_session'),
    path('chatbot/session/<int:session_id>/', views_chatbot.get_chat_session, name='get_chat_session'),
    path('chatbot/session/<int:session_id>/message/', views_chatbot.send_message, name='send_message'),
    path('chatbot/session/<int:session_id>/close/', views_chatbot.close_chat_session, name='close_chat_session'),
]
