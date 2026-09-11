# ============================================================
# CHAT SERVICE
# Primera capa de orquestación del backend
# ============================================================
from services.ai_service import generate_response

def requires_ai(message: str) -> bool:
    """
    Decide si una petición podría necesitar IA.

    Por ahora usamos una regla simple y determinista.
    Más adelante esta decisión podrá evolucionar.
    """

    normalized_message = message.lower()

    ai_keywords = [
        "explica",
        "resume",
        "analiza",
        "recomienda",
        "interpreta",
    ]

    return any(
        keyword in normalized_message
        for keyword in ai_keywords
    )


def process_message(message: str) -> str:
    """
    Procesa el mensaje y decide qué flujo utilizar.
    """

    if requires_ai(message):
                return generate_response(message, use_case="chat")

    return f"Mensaje recibido: {message}"