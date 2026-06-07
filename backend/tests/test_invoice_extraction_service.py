from pathlib import Path

from app.services.invoice_extraction_service import file_input_content


def test_pdf_file_input_uses_data_url(tmp_path: Path):
    invoice = tmp_path / "invoice.pdf"
    invoice.write_bytes(b"%PDF-1.4 fake")

    content = file_input_content(
        path=invoice,
        filename="invoice.pdf",
        content_type="application/pdf",
    )

    assert content["type"] == "input_file"
    assert content["filename"] == "invoice.pdf"
    assert content["file_data"].startswith("data:application/pdf;base64,")


def test_image_file_input_uses_data_url(tmp_path: Path):
    invoice = tmp_path / "invoice.jpg"
    invoice.write_bytes(b"\xff\xd8\xff fake")

    content = file_input_content(
        path=invoice,
        filename="invoice.jpg",
        content_type="image/jpeg",
    )

    assert content["type"] == "input_image"
    assert content["image_url"].startswith("data:image/jpeg;base64,")
    assert content["detail"] == "high"
