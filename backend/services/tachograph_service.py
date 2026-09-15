import os
from services.ai_service import generate_response
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


def generate_tachograph_analysis() -> str:
    """
    Genera un análisis mediante IA a partir del estado
    previamente calculado por las reglas de negocio.

    La IA únicamente comunica e interpreta las clasificaciones
    calculadas por el backend y no determina cumplimiento legal.
    """
    drivers = get_tachograph_status()

    message = (
        "Analiza los siguientes datos de conductores y tacógrafos.\n\n"
        "REGLAS OBLIGATORIAS:\n"
        "- Las clasificaciones NORMAL, WARNING, CRITICAL y OFFLINE "
        "han sido calculadas por el backend mediante reglas de negocio.\n"
        "- No cambies, traduzcas, recalcules ni cuestiones las clasificaciones.\n"
        "- No inventes datos que no estén presentes en la entrada.\n"
        "- No determines ni infieras cumplimiento o incumplimiento legal.\n"
        "- No inventes límites legales de conducción, descanso o jornada.\n"
        "- No determines causas de una clasificación.\n"
        "- No diagnostiques fatiga, riesgo médico ni consecuencias "
        "que no estén explícitamente presentes en los datos.\n\n"
        "INTERPRETACIÓN PERMITIDA DE LAS CLASIFICACIONES:\n"
        "- NORMAL: indica únicamente que las reglas internas del backend "
        "han clasificado el registro como NORMAL. "
        "No requiere una acción prioritaria según esta clasificación.\n"
        "- WARNING: indica únicamente que las reglas internas del backend "
        "han clasificado el registro como WARNING. "
        "Puedes recomendar revisar la situación.\n"
        "- CRITICAL: indica únicamente que las reglas internas del backend "
        "han clasificado el registro como CRITICAL. "
        "Puedes recomendar una revisión prioritaria o inmediata.\n"
        "- OFFLINE: indica únicamente que la fuente aparece como offline. "
        "Puedes recomendar comprobar su disponibilidad o conectividad.\n\n"
        "RESTRICCIONES DE LENGUAJE:\n"
        "- Los valores numéricos NO representan por sí mismos "
        "cumplimiento o incumplimiento legal.\n"
        "- No describas ningún valor como permitido, máximo legal, "
        "ilegal, excedido, incumplido o fuera de normativa.\n"
        "- No afirmes que un conductor debe realizar un descanso obligatorio "
        "basándote únicamente en estos datos.\n\n"
        "OBJETIVO:\n"
        "Resume exclusivamente los datos recibidos, identifica los registros "
        "que requieren atención según su clasificación y utiliza únicamente "
        "las interpretaciones y recomendaciones permitidas anteriormente.\n"
        "Si fuera necesaria normativa adicional para realizar una afirmación, "
        "no la asumas ni la inventes.\n\n"
        "DATOS:\n"
        f"{drivers}"
    )

    return generate_response(
        message=message,
        use_case="tachograph",
    )
