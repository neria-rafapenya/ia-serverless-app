import os
import uuid
from pathlib import Path

import boto3

ALLOWED_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "txt": "text/plain",
}


def _get_allowed_extensions() -> set[str]:
    raw_extensions = os.getenv(
        "INGESTION_ALLOWED_EXTENSIONS",
        "pdf,txt",
    )

    return {
        extension.strip().lower()
        for extension in raw_extensions.split(",")
        if extension.strip()
    }


def _get_max_file_size_bytes() -> int:
    max_size_mb = int(
        os.getenv(
            "INGESTION_MAX_FILE_SIZE_MB",
            "20",
        )
    )

    return max_size_mb * 1024 * 1024


def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def validate_document(
    filename: str,
    content_type: str,
    size_bytes: int,
) -> str:
    extension = _get_extension(filename)
    allowed_extensions = _get_allowed_extensions()

    if extension not in allowed_extensions:
        raise ValueError(f"Extensión no permitida: {extension}")

    expected_content_type = ALLOWED_CONTENT_TYPES.get(extension)

    if expected_content_type != content_type:
        raise ValueError("Content-Type no válido para la extensión indicada")

    if size_bytes <= 0:
        raise ValueError("El tamaño del archivo debe ser mayor que cero")

    max_file_size_bytes = _get_max_file_size_bytes()

    if size_bytes > max_file_size_bytes:
        raise ValueError("El archivo supera el tamaño máximo permitido")

    return extension


def generate_upload_post(
    user_id: str,
    filename: str,
    content_type: str,
    size_bytes: int,
) -> dict:
    extension = validate_document(
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
    )

    bucket = os.environ["DOCUMENTS_BUCKET"]

    object_key = f"uploads/{user_id}/" f"{uuid.uuid4()}.{extension}"

    max_file_size_bytes = _get_max_file_size_bytes()

    aws_region = os.getenv("AWS_REGION", "eu-west-1")

    s3_client = boto3.client(
        "s3",
        region_name=aws_region,
        endpoint_url=f"https://s3.{aws_region}.amazonaws.com",
    )

    presigned_post = s3_client.generate_presigned_post(
        Bucket=bucket,
        Key=object_key,
        Fields={
            "Content-Type": content_type,
        },
        Conditions=[
            {
                "Content-Type": content_type,
            },
            [
                "content-length-range",
                1,
                max_file_size_bytes,
            ],
        ],
        ExpiresIn=300,
    )

    return {
        "upload": presigned_post,
        "object_key": object_key,
        "expires_in": 300,
    }
