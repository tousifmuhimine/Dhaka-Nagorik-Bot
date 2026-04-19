"""Sync legacy local media and generated documents into Supabase Storage."""

from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from complaints.models import ChatAttachment, Complaint, ComplaintAttachment
from complaints.services.document_storage_service import DocumentStorageService
from complaints.storage_backends import SupabaseStorage


class Command(BaseCommand):
    help = "Upload legacy local attachments and generated documents into Supabase Storage."

    def handle(self, *args, **options):
        if not settings.USE_SUPABASE_STORAGE:
            raise CommandError(
                "Supabase storage is not active. Check ENABLE_SUPABASE_STORAGE and Supabase credentials."
            )

        media_storage = SupabaseStorage(bucket_name=settings.SUPABASE_MEDIA_BUCKET)
        document_storage = DocumentStorageService()

        media_synced = 0
        for attachment in list(ChatAttachment.objects.all()) + list(ComplaintAttachment.objects.all()):
            if not attachment.file.name:
                continue

            local_path = Path(settings.MEDIA_ROOT) / attachment.file.name
            if not local_path.exists() or media_storage.exists(attachment.file.name):
                continue

            with local_path.open("rb") as handle:
                media_storage.save(attachment.file.name, File(handle, name=attachment.original_name))
            media_synced += 1

        documents_synced = 0
        complaints_to_update = []
        for complaint in Complaint.objects.all():
            changed = False
            for field_name in ("generated_docx_path", "generated_pdf_path"):
                current_value = getattr(complaint, field_name)
                if not current_value:
                    continue

                local_path = Path(current_value)
                if not local_path.is_absolute() or not local_path.exists():
                    continue

                target_name = f"complaint_documents/{complaint.id}/{local_path.name}"
                if not document_storage.exists(target_name):
                    document_storage.save_bytes(target_name, local_path.read_bytes())
                setattr(complaint, field_name, target_name)
                changed = True
                documents_synced += 1

            if changed:
                complaints_to_update.append(complaint)

        for complaint in complaints_to_update:
            complaint.save(update_fields=["generated_docx_path", "generated_pdf_path", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Supabase storage sync complete. Media files uploaded: {media_synced}. "
                f"Generated documents uploaded: {documents_synced}."
            )
        )
