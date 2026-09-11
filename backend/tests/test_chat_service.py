from services.chat_service import process_message


def test_process_message_without_ai():
    response = process_message("Hola")

    assert response == "Mensaje recibido: Hola"


def test_process_message_with_ai():
    response = process_message("Analiza este documento")

    assert response == (
        "[IA simulada][chat] "
        "Procesando: Analiza este documento"
    )