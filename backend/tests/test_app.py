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