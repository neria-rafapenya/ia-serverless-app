from clients.bedrock_client import generate_text


def test_generate_text_uses_bedrock_converse(monkeypatch):
    class FakeBedrockClient:
        def converse(self, **kwargs):
            assert kwargs["modelId"] == "eu.amazon.nova-micro-v1:0"
            assert kwargs["messages"][0]["role"] == "user"
            assert kwargs["messages"][0]["content"][0]["text"] == "Hola"

            return {
                "output": {
                    "message": {
                        "content": [
                            {
                                "text": "Respuesta simulada de Bedrock"
                            }
                        ]
                    }
                }
            }

    monkeypatch.setattr(
        "clients.bedrock_client.boto3.client",
        lambda service_name: FakeBedrockClient()
    )

    response = generate_text(
        message="Hola",
        use_case="chat"
    )

    assert response == "Respuesta simulada de Bedrock"