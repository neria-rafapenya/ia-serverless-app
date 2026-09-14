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
