import os

from integrations.tachograph_source import get_tachograph_readings


def _get_warning_driving_minutes() -> int:
    return int(
        os.getenv(
            "TACHOGRAPH_WARNING_MINUTES",
            "480",
        )
    )


def _get_critical_driving_minutes() -> int:
    return int(
        os.getenv(
            "TACHOGRAPH_CRITICAL_MINUTES",
            "540",
        )
    )


def classify_reading(reading: dict) -> str:
    """
    Clasifica una lectura de tacógrafo según reglas de negocio.
    """
    if reading["status"] != "online":
        return "OFFLINE"

    driving_minutes = reading["driving_minutes_today"]

    if driving_minutes >= _get_critical_driving_minutes():
        return "CRITICAL"

    if driving_minutes >= _get_warning_driving_minutes():
        return "WARNING"

    return "NORMAL"


def get_tachograph_status() -> list[dict]:
    """
    Obtiene las lecturas y añade su clasificación.
    """
    readings = get_tachograph_readings()

    return [
        {
            **reading,
            "classification": classify_reading(reading),
        }
        for reading in readings
    ]
