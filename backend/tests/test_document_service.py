import pytest

from services import document_service


def test_validate_pdf(monkeypatch):
    monkeypatch.setenv(
        "INGESTION_ALLOWED_EXTENSIONS",
        "pdf,txt",
    )
    monkeypatch.setenv(
        "INGESTION_MAX_FILE_SIZE_MB",
        "20",
    )

    extension = document_service.validate_document(
        filename="documento.pdf",
        content_type="application/pdf",
        size_bytes=1024,
    )

    assert extension == "pdf"


def test_validate_txt(monkeypatch):
    extension = document_service.validate_document(
        filename="notas.txt",
        content_type="text/plain",
        size_bytes=500,
    )

    assert extension == "txt"


def test_rejects_invalid_extension():
    with pytest.raises(
        ValueError,
        match="Extensión no permitida",
    ):
        document_service.validate_document(
            filename="imagen.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
        )


def test_rejects_invalid_content_type():
    with pytest.raises(
        ValueError,
        match="Content-Type no válido",
    ):
        document_service.validate_document(
            filename="documento.pdf",
            content_type="text/plain",
            size_bytes=1024,
        )


def test_rejects_empty_file():
    with pytest.raises(
        ValueError,
        match="mayor que cero",
    ):
        document_service.validate_document(
            filename="documento.pdf",
            content_type="application/pdf",
            size_bytes=0,
        )


def test_rejects_file_over_max_size(monkeypatch):
    monkeypatch.setenv(
        "INGESTION_MAX_FILE_SIZE_MB",
        "20",
    )

    size_bytes = (20 * 1024 * 1024) + 1

    with pytest.raises(
        ValueError,
        match="supera el tamaño máximo",
    ):
        document_service.validate_document(
            filename="documento.pdf",
            content_type="application/pdf",
            size_bytes=size_bytes,
        )


def test_generate_upload_post(monkeypatch):
    monkeypatch.setenv(
        "DOCUMENTS_BUCKET",
        "test-documents-bucket",
    )
    monkeypatch.setenv(
        "INGESTION_ALLOWED_EXTENSIONS",
        "pdf,txt",
    )
    monkeypatch.setenv(
        "INGESTION_MAX_FILE_SIZE_MB",
        "20",
    )
    monkeypatch.setenv(
        "AWS_REGION",
        "eu-west-1",
    )

    class FakeS3Client:
        def generate_presigned_post(
            self,
            Bucket,
            Key,
            Fields,
            Conditions,
            ExpiresIn,
        ):
            assert Bucket == "test-documents-bucket"
            assert Key.startswith("uploads/user-123/")
            assert Key.endswith(".pdf")

            assert Fields == {"Content-Type": "application/pdf"}

            assert [
                "content-length-range",
                1,
                20 * 1024 * 1024,
            ] in Conditions

            assert ExpiresIn == 300

            return {
                "url": "https://example.com/upload",
                "fields": {
                    "key": Key,
                },
            }

    def fake_boto3_client(
        service,
        region_name=None,
        endpoint_url=None,
    ):
        assert service == "s3"
        assert region_name == "eu-west-1"
        assert endpoint_url == "https://s3.eu-west-1.amazonaws.com"

        return FakeS3Client()

    monkeypatch.setattr(
        document_service.boto3,
        "client",
        fake_boto3_client,
    )

    result = document_service.generate_upload_post(
        user_id="user-123",
        filename="documento.pdf",
        content_type="application/pdf",
        size_bytes=1024,
    )

    assert result["object_key"].startswith("uploads/user-123/")
    assert result["object_key"].endswith(".pdf")
    assert result["expires_in"] == 300
    assert result["upload"]["url"] == "https://example.com/upload"
