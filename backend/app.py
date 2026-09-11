import os

from fastapi import FastAPI
from pydantic import BaseModel
from services.chat_service import process_message

app = FastAPI(
    title="ia-serverless-app API",
    version="0.1.0"
)


# ============================================================
# MODELOS
# Contratos de entrada y salida de la API
# ============================================================

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    environment: str


# ============================================================
# HEALTH
# Comprueba que la API está funcionando
# ============================================================

@app.get("/health")
def health():
    return {
        "message": "ia-serverless-app funcionando",
        "environment": os.getenv("ENVIRONMENT", "unknown")
    }


# ============================================================
# CHAT
# Primera ruta funcional.
# Todavía no utiliza IA: devuelve una respuesta controlada.
# ============================================================

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    environment = os.getenv("ENVIRONMENT", "unknown")

    response = process_message(request.message)

    return ChatResponse(
        response=response,
        environment=environment
    )