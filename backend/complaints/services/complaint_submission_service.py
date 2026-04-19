"""Shared complaint submission workflow for assignment, documents, and notifications."""

from django.contrib.auth.models import User
from django.utils import timezone

from ..area_routing import normalize_city_corporation, normalize_text, same_service_area
from .document_service import ComplaintDocumentService
from .email_service import ComplaintEmailService


def normalize_area(value):
    """Normalize area/thana strings for matching."""
    return normalize_text(value)


def find_area_authority(*, city_corporation: str = '', ward_number: int | None = None, thana: str = ''):
    """Find the approved authority responsible for the complaint service area."""
    normalized_city = normalize_city_corporation(city_corporation)
    normalized_thana = normalize_area(thana)
    if not (normalized_city and ward_number) and not normalized_thana:
        return None

    queryset = (
        User.objects.filter(
            is_active=True,
            userprofile__role='authority',
            userprofile__approval_status='approved',
        )
        .select_related('userprofile')
        .order_by('id')
    )

    if normalized_city and ward_number:
        matched = queryset.filter(
            userprofile__city_corporation=normalized_city,
            userprofile__ward_number=ward_number,
        ).first()
        if matched:
            return matched

    for authority in queryset:
        profile = authority.userprofile
        if same_service_area(
            left_city_corporation=profile.city_corporation,
            left_ward_number=profile.ward_number,
            left_thana=profile.thana,
            right_city_corporation=normalized_city,
            right_ward_number=ward_number,
            right_thana=thana,
        ):
            return authority
    return None


def assign_area_authority(complaint):
    """Assign the matching area authority when the complaint does not have one yet."""
    if complaint.assigned_authority_id:
        return complaint.assigned_authority

    authority = find_area_authority(
        city_corporation=complaint.city_corporation,
        ward_number=complaint.ward_number,
        thana=complaint.thana,
    )
    if authority:
        complaint.assigned_authority = authority
        complaint.save(update_fields=['assigned_authority', 'updated_at'])
    return authority


def generate_documents_and_notify(complaint, *, extracted_complaint=None, attachments=None):
    """Generate complaint files, notify the assigned authority, and send a citizen copy."""
    attachments = attachments or []
    result = {
        'authority_assigned': False,
        'documents_generated': False,
        'authority_email_sent': False,
        'citizen_copy_sent': False,
        'email_sent': False,
        'email_error': '',
    }
    update_fields = []
    attachment_paths = []
    notification_errors = []

    authority = assign_area_authority(complaint)
    result['authority_assigned'] = bool(authority)

    if complaint.generated_docx_path and complaint.generated_pdf_path:
        attachment_paths = [complaint.generated_docx_path, complaint.generated_pdf_path]
        result['documents_generated'] = True
    else:
        try:
            generated_files = ComplaintDocumentService().generate(
                complaint=complaint,
                extracted_complaint=extracted_complaint,
                attachments=attachments,
            )
            complaint.generated_docx_path = generated_files['docx_path']
            complaint.generated_pdf_path = generated_files['pdf_path']
            attachment_paths = [complaint.generated_docx_path, complaint.generated_pdf_path]
            update_fields.extend(['generated_docx_path', 'generated_pdf_path'])
            result['documents_generated'] = True
        except Exception as doc_error:
            notification_errors.append(f'Document generation failed: {doc_error}')

    if result['documents_generated'] and not complaint.email_sent_at:
        email_service = ComplaintEmailService()

        if authority:
            authority_email_sent, authority_error = email_service.send_complaint_to_authority(
                complaint,
                attachment_paths=attachment_paths,
            )
            result['authority_email_sent'] = authority_email_sent
            result['email_sent'] = authority_email_sent
            if authority_email_sent:
                complaint.email_sent_at = timezone.now()
                update_fields.append('email_sent_at')
            elif authority_error:
                notification_errors.append(f'Authority email: {authority_error}')
        else:
            notification_errors.append('No approved authority is assigned to this complaint area yet.')

        citizen_copy_sent, citizen_error = email_service.send_citizen_delivery_copy(
            complaint,
            authority_notified=result['authority_email_sent'],
            attachment_paths=attachment_paths,
        )
        result['citizen_copy_sent'] = citizen_copy_sent
        if citizen_error:
            notification_errors.append(f'Citizen copy: {citizen_error}')

    complaint.email_error = ' | '.join(notification_errors)
    update_fields.append('email_error')

    if update_fields:
        complaint.save(update_fields=[*dict.fromkeys(update_fields), 'updated_at'])

    result['email_error'] = complaint.email_error
    return result
