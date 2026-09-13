import pytest

from services.ai_service import generate_response


def test_generate_response_uses_mock_by_default(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)

    response = generate_response(
        message="Analiza este documento",
        use_case="chat"
    )

    assert response == (
        "[IA simulada][chat] "
        "Procesando: Analiza este documento"
    )


def test_generate_response_includes_use_case(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")

    response = generate_response(
        message="Temperatura crítica",
        use_case="fridge"
    )

    assert response == (
        "[IA simulada][fridge] "
        "Procesando: Temperatura crítica"
    )


def test_generate_response_raises_error_for_unknown_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "unknown")

    with pytest.raises(ValueError):
        generate_response(
            message="Hola",
            use_case="chat"
        )

def test_generate_response_uses_bedrock_branch(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "bedrock")

    monkeypatch.setattr(
        "services.ai_service.generate_text",
        lambda message, use_case: "Respuesta Bedrock simulada"
    )

    response = generate_response(
        message="Analiza este documento",
        use_case="chat"
    )

    assert response == "Respuesta Bedrock simulada"