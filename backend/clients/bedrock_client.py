import os

import boto3


# ============================================================
# BEDROCK CLIENT
# Cliente específico para comunicarse con Amazon Bedrock
# ============================================================


DEFAULT_MODEL_ID = "eu.amazon.nova-micro-v1:0"


def generate_text(
    message: str,
    use_case: str = "general"
) -> str:
    """
    Genera texto mediante Amazon Bedrock.
    """

    model_id = os.getenv(
        "BEDROCK_MODEL_ID",
        DEFAULT_MODEL_ID
    )

    client = boto3.client("bedrock-runtime")

    response = client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": message
                    }
                ]
            }
        ],
        inferenceConfig={
            "maxTokens": 300,
            "temperature": 0.2,
        }
    )

    return response[
        "output"
    ][
        "message"
    ][
        "content"
    ][0][
        "text"
    ]