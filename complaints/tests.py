import json
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import ChatMessage, ChatSession, Complaint, ExtractedComplaint
from .services.groq_service import GroqService


class ChatbotIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="citizen@example.com",
            email="citizen@example.com",
            password="Citizen@1234",
            first_name="Citizen",
        )
        self.client.login(username="citizen@example.com", password="Citizen@1234")

    @patch("complaints.views_chatbot.WebSearchService")
    @patch("complaints.views_chatbot.GroqService")
    @patch("complaints.views_chatbot.get_rag_service")
    def test_send_message_uses_full_history_and_returns_validation(
        self,
        mock_get_rag_service,
        mock_groq_service,
        mock_web_search_service,
    ):
        session = ChatSession.objects.create(user=self.user, title="Road issue", language="en")
        ChatMessage.objects.create(chat_session=session, role="user", content="There is a road problem.")
        ChatMessage.objects.create(chat_session=session, role="assistant", content="Which area is affected?")

        mock_rag = Mock()
        mock_rag.retrieve_relevant_policies.return_value = [{
            "title": "Dhaka Road Maintenance Policy",
            "title_en": "Dhaka Road Maintenance Policy",
            "category": "roads",
            "content": "Potholes should be repaired quickly.",
            "source_file": "DNCC.pdf",
        }]
        mock_get_rag_service.return_value = mock_rag

        mock_groq = Mock()
        mock_groq.chat.return_value = "Thanks. Please share the exact road name as well."
        mock_groq.extract_complaint_info.return_value = {
            "category": "pothole",
            "area": "Dhanmondi",
            "duration": "2 weeks",
            "description": "A pothole has been on the road in Dhanmondi for two weeks.",
            "inconsistency_score": 2,
            "keywords": ["pothole", "dhanmondi", "road"],
        }
        mock_groq_service.return_value = mock_groq

        mock_web = Mock()
        mock_web.validate_against_policy.return_value = {
            "is_valid": True,
            "inconsistencies": [],
            "references": [{"title": "Recent report", "content": "Road damage in Dhanmondi.", "url": "https://example.com"}],
            "policy_references": [{"title": "Dhaka Road Maintenance Policy", "content": "Potholes should be repaired quickly."}],
            "recommendation": "This complaint is ready to file.",
        }
        mock_web_search_service.return_value = mock_web

        response = self.client.post(
            reverse("send_message", args=[session.id]),
            data=json.dumps({"message": "There is a pothole in Dhanmondi and it has been there for two weeks."}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["response"], "Thanks. Please share the exact road name as well.")
        self.assertEqual(payload["extracted_data"]["validation"]["recommendation"], "This complaint is ready to file.")

        chat_call = mock_groq.chat.call_args.kwargs
        self.assertEqual(len(chat_call["conversation_history"]), 3)
        self.assertEqual(chat_call["conversation_history"][-1]["role"], "user")
        self.assertIn("Dhaka Road Maintenance Policy", chat_call["policy_context"])

        extracted = ExtractedComplaint.objects.get(chat_session=session)
        self.assertEqual(extracted.area_thana, "Dhanmondi")
        self.assertEqual(extracted.policy_reference, "Dhaka Road Maintenance Policy")

    @patch("complaints.views_chatbot.get_rag_service")
    def test_close_chat_session_creates_complaint_once(self, mock_get_rag_service):
        session = ChatSession.objects.create(user=self.user, title="Water issue", language="en")
        ExtractedComplaint.objects.create(
            chat_session=session,
            category="water leak",
            area_thana="Mirpur",
            duration="3 days",
            keywords=["water", "mirpur"],
            inconsistency_score=2,
            full_description="A water leak has been flooding the road in Mirpur for three days.",
            policy_reference="Dhaka Water and Drainage Policy",
            web_search_results={"references": [], "policy_references": []},
        )

        mock_rag = Mock()
        mock_get_rag_service.return_value = mock_rag

        first_response = self.client.post(
            reverse("close_chat_session", args=[session.id]),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(first_response.status_code, 200)

        session.refresh_from_db()
        self.assertIsNotNone(session.generated_complaint_id)
        self.assertFalse(session.is_active)
        self.assertEqual(Complaint.objects.count(), 1)

        second_response = self.client.post(
            reverse("close_chat_session", args=[session.id]),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(Complaint.objects.count(), 1)
        self.assertEqual(
            first_response.json()["complaint_id"],
            second_response.json()["complaint_id"],
        )


class GroqServiceParsingTests(TestCase):
    def test_coerce_extraction_payload_handles_json_string_payload(self):
        service = GroqService.__new__(GroqService)
        payload = service._coerce_extraction_payload(
            '"{\\"category\\": \\"pothole\\", \\"area\\": \\"Dhanmondi\\", \\"duration\\": \\"2 weeks\\", \\"description\\": \\"Road damage\\", \\"inconsistency_score\\": 2, \\"keywords\\": [\\"pothole\\", \\"road\\"]}"',
            "user: road damage",
        )

        self.assertEqual(payload["category"], "pothole")
        self.assertEqual(payload["area"], "Dhanmondi")
