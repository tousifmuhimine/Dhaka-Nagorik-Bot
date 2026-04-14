"""Generate complaint documents for download and email delivery."""

from pathlib import Path

from django.conf import settings
from django.utils import timezone
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


class ComplaintDocumentService:
    """Generate DOCX and PDF complaint summaries."""

    def __init__(self):
        self.output_dir = Path(settings.DOCUMENT_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, complaint, extracted_complaint=None, attachments=None) -> dict:
        """Generate both document formats and return their filesystem paths."""
        attachments = attachments or []
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"complaint_{complaint.id}_{timestamp}"

        docx_path = self.output_dir / f"{base_name}.docx"
        pdf_path = self.output_dir / f"{base_name}.pdf"

        self._generate_docx(docx_path, complaint, extracted_complaint, attachments)
        self._generate_pdf(pdf_path, complaint, extracted_complaint, attachments)

        return {
            'docx_path': str(docx_path),
            'pdf_path': str(pdf_path),
        }

    def _generate_docx(self, path: Path, complaint, extracted_complaint, attachments) -> None:
        """Create a Word document for the complaint."""
        document = Document()
        document.add_heading(f'Physical Complaint Application #{complaint.id}', level=0)
        document.add_paragraph(f'Generated on: {timezone.now().strftime("%B %d, %Y %I:%M %p")}')

        details = document.add_table(rows=0, cols=2)
        rows = [
            ('Citizen', complaint.citizen.get_full_name() or complaint.citizen.username),
            ('Email', complaint.citizen.email),
            ('Category', complaint.get_category_display()),
            ('Thana', complaint.thana),
            ('Area', complaint.area),
            ('Status', complaint.get_status_display()),
            ('Created At', complaint.created_at.strftime('%B %d, %Y %I:%M %p')),
        ]
        if extracted_complaint:
            rows.extend([
                ('Duration', extracted_complaint.duration),
                ('Keywords', ', '.join(extracted_complaint.keywords or [])),
                ('Policy Reference', extracted_complaint.policy_reference),
            ])

        for label, value in rows:
            row = details.add_row().cells
            row[0].text = label
            row[1].text = value or '-'

        document.add_heading('Complaint Description', level=1)
        document.add_paragraph(complaint.description)

        if extracted_complaint:
            document.add_heading('AI Summary', level=1)
            document.add_paragraph(extracted_complaint.full_description or 'No additional AI summary available.')

            validation = extracted_complaint.web_search_results if isinstance(extracted_complaint.web_search_results, dict) else {}
            if validation:
                document.add_heading('Validation Notes', level=1)
                recommendation = validation.get('recommendation')
                if recommendation:
                    document.add_paragraph(recommendation)
                for note in validation.get('inconsistencies', []):
                    document.add_paragraph(note, style='List Bullet')

        if attachments:
            document.add_heading('Attached Photo Evidence', level=1)
            for attachment in attachments:
                document.add_paragraph(attachment.original_name, style='List Bullet')

        document.save(str(path))

    def _generate_pdf(self, path: Path, complaint, extracted_complaint, attachments) -> None:
        """Create a simple PDF complaint summary."""
        pdf = canvas.Canvas(str(path), pagesize=A4)
        width, height = A4
        x_margin = 0.8 * inch
        y = height - 0.8 * inch

        def write_line(text, font='Helvetica', size=11, leading=16):
            nonlocal y
            if y < 0.8 * inch:
                pdf.showPage()
                y = height - 0.8 * inch
            pdf.setFont(font, size)
            pdf.drawString(x_margin, y, text[:110])
            y -= leading

        write_line(f'Physical Complaint Application #{complaint.id}', 'Helvetica-Bold', 16, 22)
        write_line(f'Generated on: {timezone.now().strftime("%B %d, %Y %I:%M %p")}')
        write_line('')
        write_line(f'Citizen: {complaint.citizen.get_full_name() or complaint.citizen.username}')
        write_line(f'Email: {complaint.citizen.email}')
        write_line(f'Category: {complaint.get_category_display()}')
        write_line(f'Thana: {complaint.thana}')
        write_line(f'Area: {complaint.area}')
        write_line(f'Status: {complaint.get_status_display()}')
        if extracted_complaint:
            write_line(f'Duration: {extracted_complaint.duration or "-"}')
            write_line(f'Policy: {extracted_complaint.policy_reference or "-"}')

        write_line('')
        write_line('Complaint Description', 'Helvetica-Bold', 13, 18)
        for chunk in self._wrap_text(complaint.description):
            write_line(chunk)

        if extracted_complaint and extracted_complaint.full_description:
            write_line('')
            write_line('AI Summary', 'Helvetica-Bold', 13, 18)
            for chunk in self._wrap_text(extracted_complaint.full_description):
                write_line(chunk)

        if attachments:
            write_line('')
            write_line('Attached Photo Evidence', 'Helvetica-Bold', 13, 18)
            for attachment in attachments:
                write_line(f'- {attachment.original_name}')

        pdf.save()

    def _wrap_text(self, text: str, max_chars: int = 95):
        """Wrap long text into PDF-friendly lines."""
        words = (text or '').split()
        if not words:
            return ['-']

        lines = []
        current = []
        current_length = 0
        for word in words:
            if current and current_length + len(word) + 1 > max_chars:
                lines.append(' '.join(current))
                current = [word]
                current_length = len(word)
            else:
                current.append(word)
                current_length += len(word) + (1 if len(current) > 1 else 0)
        if current:
            lines.append(' '.join(current))
        return lines
