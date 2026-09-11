import os

from fastapi import FastAPI


app = FastAPI(
    title="ia-serverless-app API",
    version="0.1.0"
)


@app.get("/health")
def health():
    return {
        "message": "ia-serverless-app funcionando",
        "environment": os.getenv("ENVIRONMENT", "unknown")
    }