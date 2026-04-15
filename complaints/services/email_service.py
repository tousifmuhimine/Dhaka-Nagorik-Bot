"""Email delivery for complaint confirmations and generated documents."""

from email.utils import formataddr

from django.conf import settings
from django.core.mail import EmailMessage


class ComplaintEmailService:
    """Send complaint confirmation emails with generated documents."""

    def _validate_email_settings(self) -> str:
        """Return a configuration error message when email delivery is unavailable."""
        if not settings.ENABLE_EMAIL:
            return 'Email delivery is disabled by configuration.'

        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            return 'Email credentials are not configured.'

        return ''

    def _build_email(self, *, subject, body, recipients, attachment_paths=None):
        """Create an EmailMessage with the shared sender identity."""
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=formataddr((settings.EMAIL_FROM_NAME, settings.DEFAULT_FROM_EMAIL)),
            to=recipients,
        )
        for path in attachment_paths or []:
            if path:
                email.attach_file(path)
        return email

    def send_complaint_to_authority(self, complaint, attachment_paths=None) -> tuple[bool, str]:
        """Send the submitted complaint to the matched area authority."""
        config_error = self._validate_email_settings()
        if config_error:
            return False, config_error

        if not complaint.assigned_authority:
            return False, 'No authority is assigned to this complaint.'

        recipient = complaint.assigned_authority.email
        if not recipient:
            return False, 'Assigned authority email is missing.'

        subject = f'New Complaint #{complaint.id} Assigned To Your Area'
        body = (
            f"Hello {complaint.assigned_authority.get_full_name() or complaint.assigned_authority.username},\n\n"
            f"A new complaint has been routed to your area in Dhaka Nagorik AI.\n\n"
            f"Complaint ID: #{complaint.id}\n"
            f"Category: {complaint.get_category_display()}\n"
            f"Thana: {complaint.thana}\n"
            f"Area: {complaint.area}\n"
            f"Current status: {complaint.get_status_display()}\n\n"
            f"Citizen: {complaint.citizen.get_full_name() or complaint.citizen.username}\n"
            f"Citizen email: {complaint.citizen.email or 'Not provided'}\n\n"
            f"Description:\n{complaint.description}\n\n"
            "The generated complaint documents are attached for review.\n"
            "Please open the Dhaka Nagorik AI dashboard and take action.\n\n"
            "Regards,\n"
            "Dhaka Nagorik AI"
        )

        email = self._build_email(
            subject=subject,
            body=body,
            recipients=[recipient],
            attachment_paths=attachment_paths,
        )

        try:
            email.send(fail_silently=False)
            return True, ''
        except Exception as exc:
            return False, str(exc)

    def send_citizen_delivery_copy(self, complaint, authority_notified=False, attachment_paths=None) -> tuple[bool, str]:
        """Send the citizen a delivery receipt after routing the complaint."""
        config_error = self._validate_email_settings()
        if config_error:
            return False, config_error

        recipient = complaint.citizen.email
        if not recipient:
            return False, 'Citizen email is missing.'

        if complaint.assigned_authority and authority_notified:
            authority_status = (
                f"Your complaint has been delivered to "
                f"{complaint.assigned_authority.get_full_name() or complaint.assigned_authority.username}, "
                f"the authority assigned for {complaint.thana}."
            )
        elif complaint.assigned_authority:
            authority_status = (
                f"Your complaint has been assigned to "
                f"{complaint.assigned_authority.get_full_name() or complaint.assigned_authority.username}, "
                f"but the authority delivery email could not be confirmed yet."
            )
        else:
            authority_status = (
                "Your complaint has been recorded, but an approved authority has not been assigned "
                "for this area yet."
            )

        subject = f'Complaint #{complaint.id} Receipt - Dhaka Nagorik AI'
        body = (
            f"Hello {complaint.citizen.get_full_name() or complaint.citizen.username},\n\n"
            f"Your complaint #{complaint.id} has been created successfully.\n\n"
            f"{authority_status}\n\n"
            f"Category: {complaint.get_category_display()}\n"
            f"Thana: {complaint.thana}\n"
            f"Area: {complaint.area}\n"
            f"Status: {complaint.get_status_display()}\n\n"
            "A copy of the generated complaint documents is attached for your records.\n"
            "You can also track progress in the web portal.\n\n"
            "Regards,\n"
            "Dhaka Nagorik AI"
        )

        email = self._build_email(
            subject=subject,
            body=body,
            recipients=[recipient],
            attachment_paths=attachment_paths,
        )

        try:
            email.send(fail_silently=False)
            return True, ''
        except Exception as exc:
            return False, str(exc)

    def send_complaint_confirmation(self, complaint, attachment_paths=None) -> tuple[bool, str]:
        """Backward-compatible citizen receipt helper."""
        return self.send_citizen_delivery_copy(
            complaint,
            authority_notified=bool(complaint.assigned_authority_id),
            attachment_paths=attachment_paths,
        )

    def send_authority_reminder(self, complaint) -> tuple[bool, str]:
        """Send an unresolved complaint reminder to the assigned authority."""
        config_error = self._validate_email_settings()
        if config_error:
            return False, config_error

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

        email = self._build_email(
            subject=subject,
            body=body,
            recipients=[recipient],
        )

        try:
            email.send(fail_silently=False)
            return True, ''
        except Exception as exc:
            return False, str(exc)
