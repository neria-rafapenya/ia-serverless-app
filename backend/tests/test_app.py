from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "ia-serverless-app funcionando"
    assert "environment" in data


def test_chat_without_ai():
    response = client.post(
        "/api/chat",
        json={"message": "Hola"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["response"] == "Mensaje recibido: Hola"
    assert "environment" in data


def test_chat_with_ai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")

    response = client.post(
        "/api/chat",
        json={"message": "Analiza este documento"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["response"] == (
        "[IA simulada][chat] " "Procesando: Analiza este documento"
    )
    assert "environment" in data


def test_chat_rejects_empty_message():
    response = client.post(
        "/api/chat",
        json={"message": ""},
    )

    assert response.status_code == 422


def test_chat_rejects_too_long_message():
    response = client.post(
        "/api/chat",
        json={"message": "a" * 4001},
    )

    assert response.status_code == 422


def test_document_upload_url_success(monkeypatch):
    monkeypatch.setattr(
        "app.get_authenticated_user_id",
        lambda request: "user-123",
    )

    def fake_generate_upload_post(
        user_id,
        filename,
        content_type,
        size_bytes,
    ):
        assert user_id == "user-123"
        assert filename == "documento.pdf"
        assert content_type == "application/pdf"
        assert size_bytes == 1024

        return {
            "upload": {
                "url": "https://example.com/upload",
                "fields": {
                    "key": "uploads/user-123/test.pdf",
                },
            },
            "object_key": "uploads/user-123/test.pdf",
            "expires_in": 300,
        }

    monkeypatch.setattr(
        "app.generate_upload_post",
        fake_generate_upload_post,
    )

    response = client.post(
        "/api/documents/upload-url",
        json={
            "filename": "documento.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
        },
    )

    assert response.status_code == 200
    assert response.json()["object_key"] == "uploads/user-123/test.pdf"
    assert response.json()["expires_in"] == 300


def test_document_upload_url_without_authenticated_user():
    response = client.post(
        "/api/documents/upload-url",
        json={
            "filename": "documento.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
        },
    )

    assert response.status_code == 401


def test_document_upload_url_rejects_invalid_document(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.get_authenticated_user_id",
        lambda request: "user-123",
    )

    def fake_generate_upload_post(**kwargs):
        raise ValueError("Extensión no permitida: jpg")

    monkeypatch.setattr(
        "app.generate_upload_post",
        fake_generate_upload_post,
    )

    response = client.post(
        "/api/documents/upload-url",
        json={
            "filename": "imagen.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1024,
        },
    )

    assert response.status_code == 400
    assert "Extensión no permitida" in response.json()["detail"]


def test_document_upload_url_rejects_invalid_request():
    response = client.post(
        "/api/documents/upload-url",
        json={
            "filename": "documento.pdf",
            "content_type": "application/pdf",
            "size_bytes": 0,
        },
    )

    assert response.status_code == 422
