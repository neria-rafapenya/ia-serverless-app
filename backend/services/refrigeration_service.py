import os

from integrations.refrigeration_source import get_refrigeration_readings


def _get_warning_temperature() -> float:
    return float(
        os.getenv(
            "REFRIGERATION_WARNING_TEMP",
            "7.0",
        )
    )


def _get_critical_temperature() -> float:
    return float(
        os.getenv(
            "REFRIGERATION_CRITICAL_TEMP",
            "20.0",
        )
    )


def classify_reading(reading: dict) -> str:
    """
    Clasifica una lectura según las reglas de negocio.
    """

    if reading["status"] != "online":
        return "OFFLINE"

    temperature = reading["temperature"]

    if temperature >= _get_critical_temperature():
        return "CRITICAL"

    if temperature >= _get_warning_temperature():
        return "WARNING"

    return "NORMAL"


def get_refrigeration_status() -> list[dict]:
    """
    Obtiene las lecturas y añade su clasificación.
    """

    readings = get_refrigeration_readings()

    return [
        {
            **reading,
            "classification": classify_reading(reading),
        }
        for reading in readings
    ]
