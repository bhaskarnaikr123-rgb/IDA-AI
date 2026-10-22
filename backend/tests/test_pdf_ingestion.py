from pathlib import Path
from reportlab.pdfgen import canvas

from app.ingestion import ingest_document


def test_ingest_pdf_preserves_page_numbers(tmp_path: Path):
    file_path = tmp_path / "sample.pdf"

    # Create a sample PDF with two pages
    pdf = canvas.Canvas(str(file_path))
    pdf.drawString(72, 750, "Page one contains retrieval information.")
    pdf.showPage()
    pdf.drawString(72, 750, "Page two contains generation information.")
    pdf.save()

    # Ingest the PDF
    result = ingest_document(file_path)

    # Verify the extracted content
    assert result.file_type == "pdf"
    assert len(result.sections) == 2
    assert result.sections[0].page_number == 1
    assert result.sections[1].page_number == 2
    assert "retrieval information" in result.sections[0].text
    assert "generation information" in result.sections[1].text