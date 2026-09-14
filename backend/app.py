import os

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from services.chat_service import process_message
from services.document_service import generate_upload_post

app = FastAPI(title="ia-serverless-app API", version="0.1.0")


# ============================================================
# MODELOS
# Contratos de entrada y salida de la API
# ============================================================


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    response: str
    environment: str


class DocumentUploadRequest(BaseModel):
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )
    content_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    size_bytes: int = Field(
        ...,
        gt=0,
    )


class DocumentUploadResponse(BaseModel):
    upload: dict
    object_key: str
    expires_in: int


def get_authenticated_user_id(request: Request) -> str:
    event = request.scope.get("aws.event", {})

    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )

    user_id = claims.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Usuario autenticado no disponible",
        )

    return user_id


@app.post(
    "/api/documents/upload-url",
    response_model=DocumentUploadResponse,
)
def create_document_upload_url(
    payload: DocumentUploadRequest,
    request: Request,
):
    user_id = get_authenticated_user_id(request)

    try:
        result = generate_upload_post(
            user_id=user_id,
            filename=payload.filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return DocumentUploadResponse(**result)


# ============================================================
# HEALTH
# Comprueba que la API está funcionando
# ============================================================


@app.get("/health")
def health():
    return {
        "message": "ia-serverless-app funcionando",
        "environment": os.getenv("ENVIRONMENT", "unknown"),
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

    return ChatResponse(response=response, environment=environment)
