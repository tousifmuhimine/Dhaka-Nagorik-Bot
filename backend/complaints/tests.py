import json
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from docx import Document as DocxDocument
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.test.utils import override_settings

from .models import ChatAttachment, ChatMessage, ChatSession, Complaint, ComplaintActivity, ComplaintAttachment, ExtractedComplaint, UserProfile
from .services.document_storage_service import DocumentStorageService
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

    @patch("complaints.services.complaint_submission_service.ComplaintEmailService")
    @patch("complaints.services.complaint_submission_service.ComplaintDocumentService")
    @patch("complaints.views_chatbot.get_rag_service")
    def test_close_chat_session_creates_complaint_once(
        self,
        mock_get_rag_service,
        mock_document_service,
        mock_email_service,
    ):
        authority = User.objects.create_user(
            username="mirpur.authority@example.com",
            email="mirpur.authority@example.com",
            password="Authority@1234",
            first_name="Mirpur Authority",
        )
        UserProfile.objects.create(
            user=authority,
            role="authority",
            thana="Mirpur",
            approval_status="approved",
        )
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
        mock_email_service.return_value.send_complaint_to_authority.return_value = (True, "")
        mock_email_service.return_value.send_citizen_delivery_copy.return_value = (True, "")

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
        self.assertEqual(complaint.assigned_authority, authority)
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
        mock_email_service.return_value.send_complaint_to_authority.assert_called_once()
        mock_email_service.return_value.send_citizen_delivery_copy.assert_called_once()

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

    def test_get_chat_session_returns_json_for_missing_session(self):
        response = self.client.get(reverse("get_chat_session", args=[999999]))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json()["error"], "Chat session not found.")


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
                storage = DocumentStorageService()

            self.assertTrue(storage.exists(paths["docx_path"]))
            self.assertTrue(storage.exists(paths["pdf_path"]))
            doc_text = "\n".join(
                paragraph.text.strip()
                for paragraph in DocxDocument(storage.open_legacy_or_storage(paths["docx_path"])).paragraphs
                if paragraph.text.strip()
            )
            self.assertIn('APPLICATION FOR CIVIC COMPLAINT RESOLUTION', doc_text)
            self.assertIn('Subject:', doc_text)
            self.assertIn('Sir/Madam,', doc_text)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class AccessWorkflowTests(TestCase):
    def _create_user_with_profile(self, *, email, password, role, first_name, **profile_kwargs):
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            is_active=profile_kwargs.pop('is_active', True),
        )
        profile_defaults = {
            'role': role,
            'approval_status': profile_kwargs.pop('approval_status', 'approved'),
        }
        profile_defaults.update(profile_kwargs)
        UserProfile.objects.create(user=user, **profile_defaults)
        return user

    def test_authority_signup_creates_pending_inactive_account(self):
        response = self.client.post(reverse('signup'), data={
            'role': 'authority',
            'first_name': 'Area Officer',
            'city_corporation': 'DNCC',
            'ward_number': '6',
            'thana': 'Mirpur',
            'department': 'Zone Office',
            'employee_id': 'AUTH-123',
            'phone_number': '01700000000',
            'access_reason': 'I manage complaints for Mirpur.',
            'email': 'authority@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })

        self.assertRedirects(response, reverse('login'))
        user = User.objects.get(email='authority@example.com')
        profile = user.userprofile
        self.assertFalse(user.is_active)
        self.assertEqual(profile.role, 'authority')
        self.assertEqual(profile.approval_status, 'pending')
        self.assertEqual(profile.city_corporation, 'DNCC')
        self.assertEqual(profile.ward_number, 6)
        self.assertEqual(profile.thana, 'Mirpur')

    def test_authority_signup_rejects_duplicate_service_ward(self):
        self._create_user_with_profile(
            email='existing.authority@example.com',
            password='AuthorityPass123!',
            role='authority',
            first_name='Existing Authority',
            city_corporation='DSCC',
            ward_number=15,
            thana='Dhanmondi',
            department='Ward Office',
            employee_id='AUTH-001',
            phone_number='01710000000',
            access_reason='Primary ward authority.',
        )

        response = self.client.post(reverse('signup'), data={
            'role': 'authority',
            'first_name': 'Duplicate Authority',
            'city_corporation': 'DSCC',
            'ward_number': '15',
            'thana': 'Dhanmondi',
            'department': 'Second Office',
            'employee_id': 'AUTH-002',
            'phone_number': '01710000001',
            'access_reason': 'Trying to cover the same ward.',
            'email': 'duplicate.authority@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An authority account already exists or is pending for this ward.')
        self.assertFalse(User.objects.filter(email='duplicate.authority@example.com').exists())

    @patch('complaints.services.complaint_submission_service.ComplaintEmailService')
    @patch('complaints.services.complaint_submission_service.ComplaintDocumentService')
    def test_citizen_dashboard_submission_generates_documents_and_email(
        self,
        mock_document_service,
        mock_email_service,
    ):
        citizen = self._create_user_with_profile(
            email='manual.citizen@example.com',
            password='CitizenPass123!',
            role='citizen',
            first_name='Manual Citizen',
        )
        authority = self._create_user_with_profile(
            email='dhanmondi.authority@example.com',
            password='AuthorityPass123!',
            role='authority',
            first_name='Dhanmondi Authority',
            city_corporation='DSCC',
            ward_number=15,
            thana='Dhanmondi',
            department='Zone Office',
            employee_id='AUTH-321',
            phone_number='01711111111',
            access_reason='Handles Dhanmondi complaints.',
        )

        mock_document_service.return_value.generate.return_value = {
            'docx_path': 'D:/Codes/Dhaka Nagorik Bot/generated_docs/complaint_1.docx',
            'pdf_path': 'D:/Codes/Dhaka Nagorik Bot/generated_docs/complaint_1.pdf',
        }
        mock_email_service.return_value.send_complaint_to_authority.return_value = (True, '')
        mock_email_service.return_value.send_citizen_delivery_copy.return_value = (True, '')

        self.client.login(username='manual.citizen@example.com', password='CitizenPass123!')
        image = SimpleUploadedFile('pothole.jpg', b'fake-image-content', content_type='image/jpeg')
        response = self.client.post(reverse('citizen_dashboard'), data={
            'category': 'roads',
            'city_corporation': 'DSCC',
            'ward_number': '15',
            'thana': 'Dhanmondi',
            'area': 'Road 27',
            'description': 'A large pothole is blocking traffic.',
            'photos': [image],
        })

        self.assertRedirects(response, reverse('citizen_dashboard'))
        complaint = Complaint.objects.get(citizen=citizen)
        self.assertEqual(complaint.assigned_authority, authority)
        self.assertEqual(complaint.city_corporation, 'DSCC')
        self.assertEqual(complaint.ward_number, 15)
        self.assertTrue(complaint.generated_docx_path.endswith('.docx'))
        self.assertTrue(complaint.generated_pdf_path.endswith('.pdf'))
        self.assertIsNotNone(complaint.email_sent_at)
        self.assertEqual(complaint.email_error, '')
        self.assertEqual(ComplaintAttachment.objects.filter(complaint=complaint).count(), 1)
        self.assertTrue(
            ComplaintActivity.objects.filter(
                complaint=complaint,
                event_type='filed',
                actor=citizen,
            ).exists()
        )
        mock_document_service.return_value.generate.assert_called_once()
        generate_call = mock_document_service.return_value.generate.call_args.kwargs
        self.assertEqual(len(generate_call['attachments']), 1)
        self.assertEqual(generate_call['attachments'][0].original_name, 'pothole.jpg')
        mock_email_service.return_value.send_complaint_to_authority.assert_called_once()
        mock_email_service.return_value.send_citizen_delivery_copy.assert_called_once()

    def test_admin_can_approve_pending_access_request(self):
        admin_user = self._create_user_with_profile(
            email='admin@example.com',
            password='AdminPass123!',
            role='admin',
            first_name='Admin',
        )
        pending_user = self._create_user_with_profile(
            email='pending.authority@example.com',
            password='PendingPass123!',
            role='authority',
            first_name='Pending',
            approval_status='pending',
            city_corporation='DNCC',
            ward_number=19,
            thana='Banani',
            department='Ward Office',
            employee_id='AUTH-009',
            phone_number='01800000000',
            access_reason='Need access to review Banani complaints.',
            is_active=False,
        )

        self.client.login(username='admin@example.com', password='AdminPass123!')
        response = self.client.post(reverse('approve_access_request', args=[pending_user.userprofile.id]))

        self.assertRedirects(response, reverse('admin_dashboard'))
        pending_user.refresh_from_db()
        pending_user.userprofile.refresh_from_db()
        self.assertTrue(pending_user.is_active)
        self.assertEqual(pending_user.userprofile.approval_status, 'approved')
        self.assertEqual(pending_user.userprofile.approved_by, admin_user)
        self.assertIsNotNone(pending_user.userprofile.approved_at)

    def test_authority_resolution_requires_citizen_confirmation(self):
        citizen = self._create_user_with_profile(
            email='citizen.workflow@example.com',
            password='CitizenPass123!',
            role='citizen',
            first_name='Citizen',
        )
        authority = self._create_user_with_profile(
            email='authority.workflow@example.com',
            password='AuthorityPass123!',
            role='authority',
            first_name='Authority',
            city_corporation='DNCC',
            ward_number=1,
            thana='Uttara',
            department='Uttara Office',
            employee_id='AUTH-777',
            phone_number='01900000000',
            access_reason='Uttara authority access.',
        )
        complaint = Complaint.objects.create(
            citizen=citizen,
            category='roads',
            city_corporation='DNCC',
            ward_number=1,
            thana='Uttara',
            area='Sector 7',
            description='Large pothole in front of the school.',
        )

        self.client.login(username='authority.workflow@example.com', password='AuthorityPass123!')
        response = self.client.post(reverse('acknowledge_complaint', args=[complaint.id]))
        self.assertRedirects(response, reverse('complaint_detail', args=[complaint.id]))

        complaint.refresh_from_db()
        self.assertEqual(complaint.status, 'acknowledged')
        self.assertEqual(complaint.assigned_authority, authority)
        self.assertIsNotNone(complaint.acknowledged_at)

        response = self.client.post(reverse('request_resolution_confirmation', args=[complaint.id]))
        self.assertRedirects(response, reverse('complaint_detail', args=[complaint.id]))
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, 'awaiting_citizen_confirmation')
        self.assertIsNotNone(complaint.resolution_requested_at)

        self.client.logout()
        self.client.login(username='citizen.workflow@example.com', password='CitizenPass123!')
        response = self.client.post(reverse('confirm_resolution', args=[complaint.id]))
        self.assertRedirects(response, reverse('complaint_detail', args=[complaint.id]))

        complaint.refresh_from_db()
        self.assertEqual(complaint.status, 'resolved')
        self.assertIsNotNone(complaint.citizen_confirmed_at)
        self.assertIsNotNone(complaint.resolved_at)
        self.assertEqual(
            list(ComplaintActivity.objects.filter(complaint=complaint).values_list('event_type', flat=True)),
            ['acknowledged', 'resolution_requested', 'citizen_confirmed'],
        )

    @patch('complaints.views.ComplaintEmailService')
    def test_admin_reminder_email_updates_timestamp(self, mock_email_service):
        admin_user = self._create_user_with_profile(
            email='mail.admin@example.com',
            password='AdminPass123!',
            role='admin',
            first_name='Admin',
        )
        citizen = self._create_user_with_profile(
            email='mail.citizen@example.com',
            password='CitizenPass123!',
            role='citizen',
            first_name='Citizen',
        )
        authority = self._create_user_with_profile(
            email='mail.authority@example.com',
            password='AuthorityPass123!',
            role='authority',
            first_name='Authority',
            city_corporation='DNCC',
            ward_number=19,
            thana='Gulshan',
            department='Gulshan Office',
            employee_id='AUTH-555',
            phone_number='01600000000',
            access_reason='Handles Gulshan complaints.',
        )
        complaint = Complaint.objects.create(
            citizen=citizen,
            category='water',
            city_corporation='DNCC',
            ward_number=19,
            thana='Gulshan',
            area='Road 10',
            description='Water leak is flooding the road.',
            status='acknowledged',
            assigned_authority=authority,
        )

        mock_email_service.return_value.send_authority_reminder.return_value = (True, '')

        self.client.login(username='mail.admin@example.com', password='AdminPass123!')
        response = self.client.post(reverse('remind_assigned_authority', args=[complaint.id]))

        self.assertRedirects(response, reverse('admin_dashboard'))
        complaint.refresh_from_db()
        self.assertIsNotNone(complaint.last_reminder_sent_at)
        self.assertTrue(
            ComplaintActivity.objects.filter(
                complaint=complaint,
                event_type='reminder_sent',
                actor=admin_user,
            ).exists()
        )
