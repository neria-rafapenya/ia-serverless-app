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
        json={"message": "Hola"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["response"] == "Mensaje recibido: Hola"
    assert "environment" in data


def test_chat_with_ai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")

    response = client.post(
        "/api/chat",
        json={"message": "Analiza este documento"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["response"] == (
        "[IA simulada][chat] "
        "Procesando: Analiza este documento"
    )
    assert "environment" in data

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
        json={"message": "Hola"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["response"] == "Mensaje recibido: Hola"
    assert "environment" in data


def test_chat_with_ai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")

    response = client.post(
        "/api/chat",
        json={"message": "Analiza este documento"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["response"] == (
        "[IA simulada][chat] "
        "Procesando: Analiza este documento"
    )
    assert "environment" in data


def test_chat_rejects_empty_message():
    response = client.post(
        "/api/chat",
        json={"message": ""}
    )

    assert response.status_code == 422


def test_chat_rejects_too_long_message():
    response = client.post(
        "/api/chat",
        json={"message": "a" * 4001}
    )

    assert response.status_code == 422