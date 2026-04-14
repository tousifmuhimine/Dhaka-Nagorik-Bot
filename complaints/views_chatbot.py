"""Views for the chatbot functionality."""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import ChatMessage, ChatSession, Complaint, ExtractedComplaint
from .services.groq_service import GroqService
from .services.rag_service import RAGService
from .services.web_search_service import WebSearchService


MIN_MESSAGES_FOR_EXTRACTION = 2


def get_rag_service():
    """Reuse a single RAG service per process."""
    if not hasattr(get_rag_service, "_instance"):
        service = RAGService()
        service.load_policies_from_pdfs()
        get_rag_service._instance = service
    return get_rag_service._instance


def build_retrieval_query(conversation: list[dict]) -> str:
    """Build a focused retrieval query from recent user messages."""
    user_messages = [message["content"] for message in conversation if message["role"] == "user"]
    if not user_messages:
        return ""
    return "\n".join(user_messages[-3:])


def format_policy_context(policies: list[dict]) -> str:
    """Format retrieved policies for the model prompt."""
    blocks = []
    for index, policy in enumerate(policies or [], start=1):
        title = policy.get("title_en") or policy.get("title") or f"Policy {index}"
        category = policy.get("category", "general")
        content = " ".join((policy.get("content") or "").split())[:700]
        source_file = policy.get("source_file")
        source_text = f" | Source: {source_file}" if source_file else ""
        blocks.append(f"{index}. {title} | Category: {category}{source_text}\n{content}")
    return "\n\n".join(blocks)


def validation_prompt_context(validation: dict) -> str:
    """Summarize validation results into compact prompt context."""
    if not validation:
        return ""

    lines = []
    if validation.get("recommendation"):
        lines.append(f"Recommendation: {validation['recommendation']}")
    if validation.get("inconsistencies"):
        lines.append("Validation notes: " + "; ".join(validation["inconsistencies"]))
    if validation.get("references"):
        top_titles = [reference.get("title", "Reference") for reference in validation["references"][:2]]
        lines.append("Recent references: " + ", ".join(top_titles))
    return "\n".join(lines)


def normalize_extracted_value(value: str) -> str:
    """Standardize empty-ish LLM outputs."""
    text = (value or "").strip()
    if text.lower() in {"unknown", "n/a", "none", "null"}:
        return ""
    return text


def has_enough_detail(extracted_json: dict) -> bool:
    """Check whether the extracted complaint has enough detail to validate or file."""
    category = normalize_extracted_value(extracted_json.get("category", ""))
    area = normalize_extracted_value(extracted_json.get("area", ""))
    description = normalize_extracted_value(extracted_json.get("description", ""))
    return bool(category and (area or description))


def map_complaint_category(raw_category: str, description: str = "") -> str:
    """Map free-form extracted categories to the Django model choices."""
    haystack = f"{raw_category} {description}".lower()
    mapping = {
        "roads": ("road", "roads", "street", "pothole", "footpath", "traffic", "bridge"),
        "water": ("water", "drain", "drainage", "flood", "pipeline", "sewer", "sewage", "leak"),
        "electricity": ("electric", "power", "streetlight", "light", "load shedding", "cable"),
        "environment": ("garbage", "waste", "trash", "pollution", "smoke", "environment"),
        "health": ("health", "hospital", "clinic", "mosquito", "sanitation", "dengue"),
    }

    for category, keywords in mapping.items():
        if any(keyword in haystack for keyword in keywords):
            return category
    return "other"


def serialize_validation(validation_payload):
    """Normalize validation payloads stored in JSON fields."""
    if isinstance(validation_payload, dict):
        return {
            "is_valid": validation_payload.get("is_valid"),
            "inconsistencies": validation_payload.get("inconsistencies", []),
            "recommendation": validation_payload.get("recommendation", ""),
            "references": validation_payload.get("references", []),
            "policy_references": validation_payload.get("policy_references", []),
        }
    if isinstance(validation_payload, list):
        return {
            "is_valid": None,
            "inconsistencies": [],
            "recommendation": "",
            "references": validation_payload,
            "policy_references": [],
        }
    return {
        "is_valid": None,
        "inconsistencies": [],
        "recommendation": "",
        "references": [],
        "policy_references": [],
    }


def serialize_extracted_complaint(extracted: ExtractedComplaint):
    """Convert an ExtractedComplaint record to API JSON."""
    if not extracted:
        return None

    return {
        "category": extracted.category,
        "area": extracted.area_thana,
        "duration": extracted.duration,
        "keywords": extracted.keywords,
        "inconsistency_score": extracted.inconsistency_score,
        "policy_reference": extracted.policy_reference,
        "timestamp": extracted.updated_at.isoformat(),
        "validation": serialize_validation(extracted.web_search_results),
    }


def extract_complaint_info(chat_session: ChatSession):
    """Extract, validate, and persist structured complaint information."""
    messages = list(
        chat_session.messages.all()
        .values("role", "content")
        .order_by("timestamp")
    )
    if len(messages) < MIN_MESSAGES_FOR_EXTRACTION:
        return None

    rag_service = get_rag_service()
    retrieval_query = build_retrieval_query(messages)
    policies = rag_service.retrieve_relevant_policies(retrieval_query, top_k=3) if retrieval_query else []
    policy_context = format_policy_context(policies)

    groq_service = GroqService()
    extracted_json = groq_service.extract_complaint_info(messages, policy_context=policy_context)

    normalized_category = normalize_extracted_value(extracted_json.get("category", ""))
    normalized_area = normalize_extracted_value(extracted_json.get("area", ""))
    normalized_duration = normalize_extracted_value(extracted_json.get("duration", ""))
    normalized_description = normalize_extracted_value(extracted_json.get("description", ""))
    normalized_keywords = [keyword.strip() for keyword in extracted_json.get("keywords", []) if keyword and keyword.strip()]
    inconsistency_score = extracted_json.get("inconsistency_score", 3) or 3

    validation_result = {
        "is_valid": False,
        "inconsistencies": ["Need more detail before running policy and web validation."],
        "references": [],
        "policy_references": [{
            "title": policy.get("title_en") or policy.get("title") or "Policy Reference",
            "category": policy.get("category", ""),
            "content": (policy.get("content", "") or "")[:320],
            "source_file": policy.get("source_file", ""),
        } for policy in policies[:3]],
        "recommendation": "Please provide the complaint type, location, and timeline.",
    }

    if has_enough_detail(extracted_json):
        try:
            web_search_service = WebSearchService()
            validation_result = web_search_service.validate_against_policy(
                {
                    "category": normalized_category,
                    "area": normalized_area,
                    "duration": normalized_duration,
                    "description": normalized_description,
                },
                policies=policies,
            )
        except Exception as exc:
            validation_result = {
                "is_valid": False,
                "inconsistencies": [f"Validation service unavailable: {exc}"],
                "references": [],
                "policy_references": [],
                "recommendation": "The complaint was extracted, but web validation could not run.",
            }

    extracted_complaint, _ = ExtractedComplaint.objects.get_or_create(chat_session=chat_session)
    extracted_complaint.category = normalized_category
    extracted_complaint.area_thana = normalized_area
    extracted_complaint.duration = normalized_duration
    extracted_complaint.keywords = normalized_keywords
    extracted_complaint.inconsistency_score = inconsistency_score
    extracted_complaint.full_description = normalized_description
    extracted_complaint.policy_reference = (
        (validation_result.get("policy_references") or [{}])[0].get("title", "")
    )
    extracted_complaint.web_search_results = validation_result
    extracted_complaint.save()

    return serialize_extracted_complaint(extracted_complaint)


@login_required(login_url="login")
def chatbot_page(request):
    """Render the main chatbot page."""
    get_rag_service()
    chat_sessions = ChatSession.objects.filter(user=request.user, is_active=True).order_by("-updated_at")[:5]
    return render(
        request,
        "complaints/chatbot.html",
        {
            "chat_sessions": chat_sessions,
            "languages": [("en", "English"), ("bn", "Bangla")],
        },
    )


@login_required(login_url="login")
@require_http_methods(["POST"])
def create_chat_session(request):
    """Create a new chat session."""
    try:
        data = json.loads(request.body or "{}")
        language = data.get("language", "en")
        title = data.get("title", "New Complaint Chat")

        chat_session = ChatSession.objects.create(
            user=request.user,
            title=title,
            language=language,
        )

        return JsonResponse({
            "success": True,
            "session_id": chat_session.id,
            "title": chat_session.title,
            "language": chat_session.language,
        })
    except Exception as exc:
        return JsonResponse({
            "success": False,
            "error": str(exc),
        }, status=400)


@login_required(login_url="login")
@require_http_methods(["POST"])
def send_message(request, session_id):
    """Send a message in a chat session and get an AI response."""
    chat_session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    try:
        data = json.loads(request.body or "{}")
        user_message = (data.get("message") or "").strip()
        if not user_message:
            return JsonResponse({"success": False, "error": "Empty message"}, status=400)

        ChatMessage.objects.create(
            chat_session=chat_session,
            role="user",
            content=user_message,
        )

        conversation_history = list(
            chat_session.messages.all()
            .values("role", "content")
            .order_by("timestamp")
        )

        rag_service = get_rag_service()
        retrieval_query = build_retrieval_query(conversation_history)
        policies = rag_service.retrieve_relevant_policies(retrieval_query, top_k=3) if retrieval_query else []
        policy_context = format_policy_context(policies)

        existing_validation = None
        if hasattr(chat_session, "extracted_complaint"):
            existing_validation = serialize_validation(chat_session.extracted_complaint.web_search_results)

        if chat_session.language == "bn":
            system_prompt = (
                "আপনি ঢাকা শহরের নাগরিক অভিযোগ সহায়ক। ব্যবহারকারীদের অবকাঠামো, "
                "ইউটিলিটি এবং জনসেবা সংক্রান্ত অভিযোগ স্পষ্টভাবে গুছিয়ে তুলতে সাহায্য করুন। "
                "বন্ধুসুলভ থাকুন, এবং দরকার হলে অভিযোগের ধরন, থানা/এলাকা, ও কতদিন ধরে সমস্যা "
                "চলছে তা জিজ্ঞেস করুন।"
            )
        else:
            system_prompt = (
                "You are a civic complaint assistant for Dhaka city. Help users file clear, "
                "actionable complaints about infrastructure, utilities, and public services. "
                "Use the retrieved policy context when it is relevant, and ask follow-up questions "
                "when complaint type, location, or duration are still missing."
            )

        groq_service = GroqService()
        ai_response = groq_service.chat(
            conversation_history=conversation_history,
            system_prompt=system_prompt,
            policy_context=policy_context,
            validation_context=validation_prompt_context(existing_validation),
        )

        ChatMessage.objects.create(
            chat_session=chat_session,
            role="assistant",
            content=ai_response,
        )
        chat_session.save()

        extracted_data = extract_complaint_info(chat_session)

        return JsonResponse({
            "success": True,
            "response": ai_response,
            "timestamp": timezone.now().isoformat(),
            "extracted_data": extracted_data,
        })
    except Exception as exc:
        return JsonResponse({
            "success": False,
            "error": str(exc),
        }, status=400)


@login_required(login_url="login")
def get_chat_session(request, session_id):
    """Get messages from a chat session."""
    chat_session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    messages = chat_session.messages.all().values("id", "role", "content", "timestamp").order_by("timestamp")

    extracted_data = None
    if hasattr(chat_session, "extracted_complaint"):
        extracted_data = serialize_extracted_complaint(chat_session.extracted_complaint)

    return JsonResponse({
        "success": True,
        "session": {
            "id": chat_session.id,
            "title": chat_session.title,
            "language": chat_session.language,
            "generated_complaint_id": chat_session.generated_complaint_id,
            "complaint_detail_url": (
                reverse("complaint_detail", args=[chat_session.generated_complaint_id])
                if chat_session.generated_complaint_id else None
            ),
        },
        "messages": list(messages),
        "extracted_data": extracted_data,
    })


@login_required(login_url="login")
@require_http_methods(["POST"])
def close_chat_session(request, session_id):
    """Close a chat session and create a formal complaint if possible."""
    chat_session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    try:
        if not hasattr(chat_session, "extracted_complaint"):
            extracted_data = extract_complaint_info(chat_session)
            if not extracted_data:
                return JsonResponse({
                    "success": False,
                    "error": "The chat does not have enough information to create a complaint yet.",
                }, status=400)

        extracted_complaint = chat_session.extracted_complaint
        category = map_complaint_category(extracted_complaint.category, extracted_complaint.full_description)
        area = normalize_extracted_value(extracted_complaint.area_thana)
        description = normalize_extracted_value(extracted_complaint.full_description)

        if not area or not description:
            return JsonResponse({
                "success": False,
                "error": "Need both a location and a complaint description before filing.",
            }, status=400)

        if chat_session.generated_complaint_id:
            complaint = chat_session.generated_complaint
        else:
            complaint = Complaint.objects.create(
                citizen=request.user,
                category=category,
                thana=area,
                area=area,
                description=description,
            )
            chat_session.generated_complaint = complaint
            chat_session.is_active = False
            chat_session.save(update_fields=["generated_complaint", "is_active", "updated_at"])

            try:
                rag_service = get_rag_service()
                summary = f"{complaint.category} complaint in {complaint.area}. {complaint.description}"
                rag_service.store_complaint_summary(
                    complaint_id=str(complaint.id),
                    summary=summary,
                    category=complaint.category,
                )
            except Exception:
                pass

        return JsonResponse({
            "success": True,
            "message": "Complaint created successfully.",
            "complaint_id": complaint.id,
            "complaint_detail_url": reverse("complaint_detail", args=[complaint.id]),
        })
    except Exception as exc:
        return JsonResponse({
            "success": False,
            "error": str(exc),
        }, status=400)
