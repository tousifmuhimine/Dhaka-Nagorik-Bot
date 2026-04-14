import json
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.test.utils import override_settings

from .models import ChatAttachment, ChatMessage, ChatSession, Complaint, ExtractedComplaint
from .services.document_service import ComplaintDocumentService
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
        self.assertEqual(payload["user_message"]["role"], "user")
        self.assertEqual(payload["assistant_message"]["role"], "assistant")

        chat_call = mock_groq.chat.call_args.kwargs
        self.assertEqual(len(chat_call["conversation_history"]), 3)
        self.assertEqual(chat_call["conversation_history"][-1]["role"], "user")
        self.assertIn("Dhaka Road Maintenance Policy", chat_call["policy_context"])

        extracted = ExtractedComplaint.objects.get(chat_session=session)
        self.assertEqual(extracted.area_thana, "Dhanmondi")
        self.assertEqual(extracted.policy_reference, "Dhaka Road Maintenance Policy")

    @patch("complaints.views_chatbot.ComplaintEmailService")
    @patch("complaints.views_chatbot.ComplaintDocumentService")
    @patch("complaints.views_chatbot.get_rag_service")
    def test_close_chat_session_creates_complaint_once(
        self,
        mock_get_rag_service,
        mock_document_service,
        mock_email_service,
    ):
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
        mock_document_service.return_value.generate.return_value = {
            "docx_path": "D:/Codes/Dhaka Nagorik Bot/generated_docs/complaint_1.docx",
            "pdf_path": "D:/Codes/Dhaka Nagorik Bot/generated_docs/complaint_1.pdf",
        }
        mock_email_service.return_value.send_complaint_confirmation.return_value = (True, "")

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
        complaint = Complaint.objects.get()
        self.assertTrue(complaint.generated_docx_path.endswith(".docx"))
        self.assertTrue(complaint.generated_pdf_path.endswith(".pdf"))
        self.assertIsNotNone(complaint.email_sent_at)

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
        mock_document_service.return_value.generate.assert_called_once()
        mock_email_service.return_value.send_complaint_confirmation.assert_called_once()

    @patch("complaints.views_chatbot.WebSearchService")
    @patch("complaints.views_chatbot.GroqService")
    @patch("complaints.views_chatbot.get_rag_service")
    def test_send_message_accepts_photo_uploads(
        self,
        mock_get_rag_service,
        mock_groq_service,
        mock_web_search_service,
    ):
        session = ChatSession.objects.create(user=self.user, title="Garbage issue", language="en")

        mock_rag = Mock()
        mock_rag.retrieve_relevant_policies.return_value = []
        mock_get_rag_service.return_value = mock_rag

        mock_groq = Mock()
        mock_groq.chat.return_value = "Thanks for the photo evidence. Please share the exact address too."
        mock_groq.extract_complaint_info.return_value = {
            "category": "garbage",
            "area": "Banani",
            "duration": "3 days",
            "description": "Garbage has been piling up in Banani for three days.",
            "inconsistency_score": 2,
            "keywords": ["garbage", "banani"],
        }
        mock_groq_service.return_value = mock_groq

        mock_web = Mock()
        mock_web.validate_against_policy.return_value = {
            "is_valid": True,
            "inconsistencies": [],
            "references": [],
            "policy_references": [],
            "recommendation": "Looks ready for filing.",
        }
        mock_web_search_service.return_value = mock_web

        image = SimpleUploadedFile("evidence.jpg", b"fake-image-content", content_type="image/jpeg")
        response = self.client.post(
            reverse("send_message", args=[session.id]),
            data={"message": "See this garbage pile.", "photos": [image]},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["user_message"]["attachments"]), 1)
        self.assertEqual(ChatAttachment.objects.count(), 1)
        history = mock_groq.chat.call_args.kwargs["conversation_history"]
        self.assertIn("Attached photo evidence", history[-1]["content"])


class GroqServiceParsingTests(TestCase):
    def test_coerce_extraction_payload_handles_json_string_payload(self):
        service = GroqService.__new__(GroqService)
        payload = service._coerce_extraction_payload(
            '"{\\"category\\": \\"pothole\\", \\"area\\": \\"Dhanmondi\\", \\"duration\\": \\"2 weeks\\", \\"description\\": \\"Road damage\\", \\"inconsistency_score\\": 2, \\"keywords\\": [\\"pothole\\", \\"road\\"]}"',
            "user: road damage",
        )

        self.assertEqual(payload["category"], "pothole")
        self.assertEqual(payload["area"], "Dhanmondi")


class ComplaintDocumentServiceTests(TestCase):
    def test_generate_creates_docx_and_pdf(self):
        user = User.objects.create_user(
            username="docuser@example.com",
            email="docuser@example.com",
            password="Password123!",
        )
        complaint = Complaint.objects.create(
            citizen=user,
            category="roads",
            thana="Dhanmondi",
            area="Road 27",
            description="There is a dangerous pothole on Road 27.",
        )
        session = ChatSession.objects.create(user=user, generated_complaint=complaint)
        extracted = ExtractedComplaint.objects.create(
            chat_session=session,
            category="pothole",
            area_thana="Dhanmondi",
            duration="2 weeks",
            keywords=["pothole", "road"],
            policy_reference="Dhaka Road Maintenance Policy",
            full_description="A pothole has made the road unsafe for vehicles and pedestrians.",
            web_search_results={"references": [], "policy_references": []},
        )

        temp_dir = Path('test_generated_docs')
        temp_dir.mkdir(exist_ok=True)
        try:
            with override_settings(DOCUMENT_OUTPUT_DIR=str(temp_dir.resolve())):
                service = ComplaintDocumentService()
                paths = service.generate(complaint, extracted_complaint=extracted, attachments=[])

            self.assertTrue(Path(paths["docx_path"]).exists())
            self.assertTrue(Path(paths["pdf_path"]).exists())
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
