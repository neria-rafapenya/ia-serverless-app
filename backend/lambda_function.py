import json


def lambda_handler(event, context):
    """
    Punto de entrada de nuestra primera Lambda.
    """

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "ia-serverless-app funcionando",
            "environment": "dev"
        })
    }