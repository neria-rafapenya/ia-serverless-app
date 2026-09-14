import json
import os
from pathlib import Path

MOCK_DATA_FILE = Path(__file__).parent.parent / "mocks" / "refrigeration_data.json"


def get_refrigeration_readings() -> list[dict]:
    """
    Obtiene las lecturas de los dispositivos de refrigeración
    desde la fuente configurada.
    """
    source = os.getenv(
        "REFRIGERATION_SOURCE",
        "mock",
    )

    if source == "mock":
        return _get_mock_readings()

    if source == "api":
        return _get_api_readings()

    raise ValueError(f"Fuente de refrigeración no soportada: {source}")


def _get_mock_readings() -> list[dict]:
    with MOCK_DATA_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def _get_api_readings() -> list[dict]:
    raise NotImplementedError(
        "La integración con la API de refrigeración " "todavía no está implementada"
    )
