import os

from clients.bedrock_client import generate_text

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

    Proveedores soportados:
    - mock
    - bedrock
    """

    provider = os.getenv("AI_PROVIDER", "mock")

    if provider == "mock":
        return _generate_mock_response(message, use_case)

    if provider == "bedrock":
        return _generate_bedrock_response(message, use_case)

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


def _generate_bedrock_response(
    message: str,
    use_case: str
) -> str:
    return generate_text(
        message=message,
        use_case=use_case
    )