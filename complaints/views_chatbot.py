"""Views for the chatbot functionality."""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import ChatSession, ChatMessage, ExtractedComplaint, UserProfile
from .services.groq_service import GroqService
from .services.rag_service import RAGService
from .services.web_search_service import WebSearchService


@login_required(login_url='login')
def chatbot_page(request):
    """Render the main chatbot page."""
    # Get or create RAG service singleton
    if not hasattr(chatbot_page, '_rag_service'):
        chatbot_page._rag_service = RAGService()
        chatbot_page._rag_service.load_policies_from_pdfs()
    
    # Get user's recent chat sessions
    chat_sessions = ChatSession.objects.filter(user=request.user, is_active=True).order_by('-updated_at')[:5]
    
    context = {
        'chat_sessions': chat_sessions,
        'languages': [('en', 'English'), ('bn', 'Bangla')],
    }
    
    return render(request, 'complaints/chatbot.html', context)


@login_required(login_url='login')
@require_http_methods(["POST"])
def create_chat_session(request):
    """Create a new chat session."""
    try:
        data = json.loads(request.body)
        language = data.get('language', 'en')
        title = data.get('title', 'New Complaint Chat')
        
        chat_session = ChatSession.objects.create(
            user=request.user,
            title=title,
            language=language
        )
        
        return JsonResponse({
            'success': True,
            'session_id': chat_session.id,
            'title': chat_session.title,
            'language': chat_session.language
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required(login_url='login')
@require_http_methods(["POST"])
def send_message(request, session_id):
    """Send a message in a chat session and get AI response."""
    chat_session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'success': False, 'error': 'Empty message'}, status=400)
        
        # Save user message
        ChatMessage.objects.create(
            chat_session=chat_session,
            role='user',
            content=user_message
        )
        
        # Get AI response
        groq_service = GroqService()
        
        # Get conversation history
        messages = chat_session.messages.all().values('role', 'content').order_by('timestamp')
        conversation_history = list(messages)
        
        # Get system prompt based on language
        if chat_session.language == 'bn':
            system_prompt = """আপনি ঢাকা শহরের নাগরিক অভিযোগ সহায়ক। ব্যবহারকারীদের অবকাঠামো, ইউটিলিটি এবং জনসেবা সম্পর্কে অভিযোগ করতে সাহায্য করুন।
        কথোপকথনমূলক হন এবং প্রয়োজনীয় তথ্য চিহ্নিত করুন: অভিযোগের ধরন, অবস্থান (থানা), এবং সময়কাল।"""
        else:
            system_prompt = """You are a civic complaint assistant for Dhaka city. Help users file complaints about infrastructure, utilities, and public services.
        Be conversational and extract key information: complaint type, location (thana), and duration."""
        
        # Get AI response
        ai_response = groq_service.chat(user_message, system_prompt)
        
        # Save AI response
        ChatMessage.objects.create(
            chat_session=chat_session,
            role='assistant',
            content=ai_response
        )
        
        # Update chat session timestamp
        chat_session.save()
        
        # Check if we should extract complaint info (after 3+ messages)
        message_count = chat_session.messages.count()
        extracted_data = None
        
        if message_count >= 6:  # User + AI pairs
            # Extract complaint information
            extracted_data = extract_complaint_info(chat_session)
        
        return JsonResponse({
            'success': True,
            'response': ai_response,
            'timestamp': timezone.now().isoformat(),
            'extracted_data': extracted_data
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def extract_complaint_info(chat_session):
    """Extract structured complaint information from chat."""
    try:
        # Get all messages
        messages = chat_session.messages.all().values_list('role', 'content').order_by('timestamp')
        conversation = [{'role': role, 'content': content} for role, content in messages]
        
        # Use Groq to extract information
        groq_service = GroqService()
        extracted_json = groq_service.extract_complaint_info(conversation)
        
        # Create or update ExtractedComplaint
        extracted_complaint, created = ExtractedComplaint.objects.get_or_create(
            chat_session=chat_session,
            defaults={
                'category': extracted_json.get('category', ''),
                'area_thana': extracted_json.get('area', ''),
                'duration': extracted_json.get('duration', ''),
                'keywords': extracted_json.get('keywords', []),
                'inconsistency_score': extracted_json.get('inconsistency_score', 3),
                'full_description': extracted_json.get('description', ''),
            }
        )
        
        # Perform web search for validation
        web_search_service = WebSearchService()
        validation_result = web_search_service.validate_against_policy(extracted_json)
        extracted_complaint.web_search_results = validation_result.get('references', [])
        extracted_complaint.save()
        
        return {
            'category': extracted_complaint.category,
            'area': extracted_complaint.area_thana,
            'duration': extracted_complaint.duration,
            'keywords': extracted_complaint.keywords,
            'inconsistency_score': extracted_complaint.inconsistency_score,
            'timestamp': extracted_complaint.extracted_at.isoformat(),
            'validation': {
                'is_valid': validation_result.get('is_valid'),
                'inconsistencies': validation_result.get('inconsistencies', []),
                'recommendation': validation_result.get('recommendation', '')
            }
        }
    except Exception as e:
        print(f"Error extracting complaint info: {e}")
        return None


@login_required(login_url='login')
def get_chat_session(request, session_id):
    """Get messages from a chat session."""
    chat_session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    
    messages = chat_session.messages.all().values('id', 'role', 'content', 'timestamp').order_by('timestamp')
    
    extracted_data = None
    if hasattr(chat_session, 'extracted_complaint'):
        extracted = chat_session.extracted_complaint
        extracted_data = {
            'category': extracted.category,
            'area': extracted.area_thana,
            'duration': extracted.duration,
            'keywords': extracted.keywords,
            'inconsistency_score': extracted.inconsistency_score,
            'timestamp': extracted.extracted_at.isoformat(),
        }
    
    return JsonResponse({
        'success': True,
        'session': {
            'id': chat_session.id,
            'title': chat_session.title,
            'language': chat_session.language,
        },
        'messages': list(messages),
        'extracted_data': extracted_data
    })


@login_required(login_url='login')
def close_chat_session(request, session_id):
    """Close a chat session (finalize complaint)."""
    chat_session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    
    try:
        chat_session.is_active = False
        chat_session.save()
        
        # Optionally create a formal Complaint from the chat
        extracted_complaint = getattr(chat_session, 'extracted_complaint', None)
        
        if extracted_complaint:
            complaint_data = {
                'citizen': request.user,
                'category': extracted_complaint.category,
                'thana': extracted_complaint.area_thana,
                'area': extracted_complaint.area_thana,
                'description': extracted_complaint.full_description,
            }
            # Could import Complaint model and create here
        
        return JsonResponse({
            'success': True,
            'message': 'Chat session closed'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
