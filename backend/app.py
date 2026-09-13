import os

from fastapi import FastAPI
from pydantic import BaseModel, Field
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
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000
    )

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
# Procesa el mensaje y delega en el servicio de chat.
# El servicio decide si la petición requiere IA.
# ============================================================

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    environment = os.getenv("ENVIRONMENT", "unknown")

    response = process_message(request.message)

    return ChatResponse(
        response=response,
        environment=environment
    )