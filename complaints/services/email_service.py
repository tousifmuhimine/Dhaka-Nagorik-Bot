"""Email delivery for complaint confirmations and generated documents."""

from email.utils import formataddr

from django.conf import settings
from django.core.mail import EmailMessage


class ComplaintEmailService:
    """Send complaint confirmation emails with generated documents."""

    def send_complaint_confirmation(self, complaint, attachment_paths=None) -> tuple[bool, str]:
        """Send a confirmation email to the citizen."""
        attachment_paths = attachment_paths or []

        if not settings.ENABLE_EMAIL:
            return False, 'Email delivery is disabled by configuration.'

        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            return False, 'Email credentials are not configured.'

        recipient = complaint.citizen.email
        if not recipient:
            return False, 'Citizen email is missing.'

        subject = f'Complaint #{complaint.id} Submitted - Dhaka Nagorik AI'
        body = (
            f"Hello {complaint.citizen.get_full_name() or complaint.citizen.username},\n\n"
            f"Your complaint #{complaint.id} has been created successfully.\n\n"
            f"Category: {complaint.get_category_display()}\n"
            f"Thana: {complaint.thana}\n"
            f"Area: {complaint.area}\n"
            f"Status: {complaint.get_status_display()}\n\n"
            "We attached the generated complaint documents for your physical application.\n"
            "You can also track progress in the web portal.\n\n"
            "Regards,\n"
            "Dhaka Nagorik AI"
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=formataddr((settings.EMAIL_FROM_NAME, settings.DEFAULT_FROM_EMAIL)),
            to=[recipient],
        )

        for path in attachment_paths:
            if path:
                email.attach_file(path)

        try:
            email.send(fail_silently=False)
            return True, ''
        except Exception as exc:
            return False, str(exc)

    def send_authority_reminder(self, complaint) -> tuple[bool, str]:
        """Send an unresolved complaint reminder to the assigned authority."""
        if not settings.ENABLE_EMAIL:
            return False, 'Email delivery is disabled by configuration.'

        if not complaint.assigned_authority:
            return False, 'No authority is assigned to this complaint.'

        recipient = complaint.assigned_authority.email
        if not recipient:
            return False, 'Assigned authority email is missing.'

        subject = f'Reminder: Complaint #{complaint.id} Needs Attention'
        body = (
            f"Hello {complaint.assigned_authority.get_full_name() or complaint.assigned_authority.username},\n\n"
            f"Complaint #{complaint.id} is still pending action.\n\n"
            f"Category: {complaint.get_category_display()}\n"
            f"Thana: {complaint.thana}\n"
            f"Area: {complaint.area}\n"
            f"Current status: {complaint.get_status_display()}\n\n"
            f"Description:\n{complaint.description}\n\n"
            "Please review the complaint in the Dhaka Nagorik AI dashboard.\n\n"
            "Regards,\n"
            "Dhaka Nagorik AI"
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=formataddr((settings.EMAIL_FROM_NAME, settings.DEFAULT_FROM_EMAIL)),
            to=[recipient],
        )

        try:
            email.send(fail_silently=False)
            return True, ''
        except Exception as exc:
            return False, str(exc)
