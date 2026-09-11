import os


# ============================================================
# AI SERVICE
# Capa común de acceso a servicios de Inteligencia Artificial
# ============================================================


def generate_response(
    message: str,
    use_case: str = "general"
) -> str:
    """
    Genera una respuesta utilizando el proveedor de IA configurado.

    use_case permite indicar quién está utilizando la IA:
    - chat
    - fridge
    - document
    - general
    """

    provider = os.getenv("AI_PROVIDER", "mock")

    if provider == "mock":
        return _generate_mock_response(message, use_case)

    raise ValueError(
        f"Proveedor de IA no soportado: {provider}"
    )


def _generate_mock_response(
    message: str,
    use_case: str
) -> str:
    """
    Implementación simulada.

    No realiza ninguna llamada externa ni genera coste.
    """

    return (
        f"[IA simulada][{use_case}] "
        f"Procesando: {message}"
    )