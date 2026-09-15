from services.refrigeration_service import classify_reading


def test_classify_normal_reading():
    reading = {
        "temperature": 4.2,
        "status": "online",
    }

    assert classify_reading(reading) == "NORMAL"


def test_classify_warning_reading():
    reading = {
        "temperature": 7.8,
        "status": "online",
    }

    assert classify_reading(reading) == "WARNING"


def test_classify_critical_reading():
    reading = {
        "temperature": 22.4,
        "status": "online",
    }

    assert classify_reading(reading) == "CRITICAL"


def test_classify_offline_reading():
    reading = {
        "temperature": 5.1,
        "status": "offline",
    }

    assert classify_reading(reading) == "OFFLINE"


def test_generate_refrigeration_analysis(monkeypatch):
    def mock_generate_response(message, use_case):
        assert "FRIDGE-003" in message
        assert "CRITICAL" in message
        assert use_case == "refrigeration"

        assert "No inventes datos" in message
        assert "No inventes límites de temperatura" in message
        assert "No determines causas" in message
        assert "No infieras averías" in message
        assert "daños en mercancía o alimentos" in message
        assert "INTERPRETACIÓN PERMITIDA" in message
        assert "WARNING" in message
        assert "CRITICAL" in message
        assert "No cambies, traduzcas, recalcules ni cuestiones" in message

        return "Análisis de refrigeración generado"

    monkeypatch.setattr(
        "services.refrigeration_service.generate_response",
        mock_generate_response,
    )

    from services.refrigeration_service import (
        generate_refrigeration_analysis,
    )

    result = generate_refrigeration_analysis()

    assert result == "Análisis de refrigeración generado"
