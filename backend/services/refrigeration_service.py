import os
from services.ai_service import generate_response
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


def generate_refrigeration_analysis() -> str:
    """
    Genera un análisis mediante IA a partir del estado
    previamente calculado por las reglas de negocio.

    La IA únicamente comunica e interpreta las clasificaciones
    calculadas por el backend.
    """
    devices = get_refrigeration_status()

    message = (
        "Analiza los siguientes datos de dispositivos de refrigeración.\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "- Las clasificaciones NORMAL, WARNING, CRITICAL y OFFLINE "
        "han sido calculadas por el backend mediante reglas de negocio.\n"
        "- No cambies, traduzcas, recalcules ni cuestiones las clasificaciones.\n"
        "- No inventes datos que no estén presentes en la entrada.\n"
        "- No inventes límites de temperatura ni normativa.\n"
        "- No determines causas de una clasificación.\n"
        "- No infieras averías, daños en mercancía o alimentos, pérdidas "
        "de producto, riesgos sanitarios, consecuencias económicas "
        "ni ninguna otra consecuencia no incluida en los datos.\n"
        "- No afirmes que un dispositivo incumple una norma o requisito legal.\n\n"
        "INTERPRETACIÓN PERMITIDA DE LAS CLASIFICACIONES:\n"
        "- NORMAL: indica únicamente que las reglas internas del backend "
        "han clasificado el dispositivo como NORMAL. "
        "No requiere una acción prioritaria según esta clasificación.\n"
        "- WARNING: indica únicamente que las reglas internas del backend "
        "han clasificado el dispositivo como WARNING. "
        "Puedes recomendar revisión o seguimiento.\n"
        "- CRITICAL: indica únicamente que las reglas internas del backend "
        "han clasificado el dispositivo como CRITICAL. "
        "Puedes recomendar una revisión prioritaria o inmediata.\n"
        "- OFFLINE: indica únicamente que el dispositivo aparece como offline. "
        "Puedes recomendar comprobar su disponibilidad o conectividad.\n\n"
        "OBJETIVO:\n"
        "Resume exclusivamente los datos recibidos, identifica los dispositivos "
        "que requieren atención según su clasificación y utiliza únicamente "
        "las interpretaciones y recomendaciones permitidas anteriormente.\n"
        "Si los datos no permiten conocer una causa o consecuencia, no la asumas.\n\n"
        "DATOS:\n"
        f"{devices}"
    )

    return generate_response(
        message=message,
        use_case="refrigeration",
    )
