from services.tachograph_service import classify_reading


def test_classify_normal_reading():
    reading = {
        "driving_minutes_today": 240,
        "status": "online",
    }

    assert classify_reading(reading) == "NORMAL"


def test_classify_warning_reading():
    reading = {
        "driving_minutes_today": 510,
        "status": "online",
    }

    assert classify_reading(reading) == "WARNING"


def test_classify_critical_reading():
    reading = {
        "driving_minutes_today": 570,
        "status": "online",
    }

    assert classify_reading(reading) == "CRITICAL"


def test_classify_offline_reading():
    reading = {
        "driving_minutes_today": 180,
        "status": "offline",
    }

    assert classify_reading(reading) == "OFFLINE"


def test_generate_tachograph_analysis(monkeypatch):
    def mock_generate_response(message, use_case):
        assert "DRIVER-003" in message
        assert "CRITICAL" in message
        assert use_case == "tachograph"

        assert "No inventes datos" in message
        assert "No determines ni infieras cumplimiento" in message
        assert "No inventes límites legales" in message
        assert "No determines causas" in message
        assert "INTERPRETACIÓN PERMITIDA" in message
        assert "RESTRICCIONES DE LENGUAJE" in message
        assert "máximo legal" in message
        assert "descanso obligatorio" in message
        assert "No cambies, traduzcas, recalcules ni cuestiones" in message

        return "Análisis de tacógrafo generado"

    monkeypatch.setattr(
        "services.tachograph_service.generate_response",
        mock_generate_response,
    )

    from services.tachograph_service import (
        generate_tachograph_analysis,
    )

    result = generate_tachograph_analysis()

    assert result == "Análisis de tacógrafo generado"
