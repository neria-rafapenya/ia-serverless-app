# ============================================================
# CHAT SERVICE
# Lógica de negocio relacionada con el chat
# ============================================================


def process_message(message: str) -> str:
    """
    Procesa un mensaje recibido por la API.

    Por ahora devuelve una respuesta determinista.
    Más adelante esta capa podrá decidir si necesita:
    - reglas de negocio
    - RAG
    - Bedrock
    - llamadas a servicios externos
    """

    return f"Mensaje recibido: {message}"