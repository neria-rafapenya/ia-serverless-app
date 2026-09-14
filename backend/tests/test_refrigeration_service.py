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
