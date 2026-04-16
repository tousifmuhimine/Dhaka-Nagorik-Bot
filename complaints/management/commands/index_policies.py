"""Management command to index policy documents into the configured vector store."""

from django.core.management.base import BaseCommand

from complaints.services.rag_service import RAGService


class Command(BaseCommand):
    help = "Index policy PDFs (or fallback sample policies) into the configured vector store."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pdf-dir",
            dest="pdf_dir",
            help="Optional directory containing policy PDF files.",
        )

    def handle(self, *args, **options):
        service = RAGService()
        loaded = service.load_policies_from_pdfs(pdf_dir=options.get("pdf_dir"))

        if loaded:
            self.stdout.write(self.style.SUCCESS("Policy vectors indexed successfully."))
            return

        self.stderr.write(self.style.ERROR("Policy indexing did not complete successfully."))
