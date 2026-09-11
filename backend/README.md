# Backend — ia-serverless-app

Este directorio contiene el backend de `ia-serverless-app`.

El backend se construye como una API Python con **FastAPI**, ejecutada de forma serverless en **AWS Lambda**. **Mangum** actúa como adaptador entre Lambda/API Gateway y la aplicación ASGI de FastAPI.

## Arquitectura actual

```text
Internet
   |
   v
API Gateway HTTP API
   |
   v
AWS Lambda
   |
   v
Mangum
   |
   v
FastAPI
   |
   +--> GET /health
   |
   +--> POST /api/chat
```

Actualmente esta arquitectura está desplegada y ambas rutas han sido probadas correctamente.

## Versiones actuales

```text
Python   3.12
FastAPI  0.141.1
Mangum   0.22.0
```

AWS Lambda utiliza el runtime `python3.12`.

## Estructura

```text
backend/
├── app.py
├── lambda_function.py
├── requirements.txt
└── README.md
```

## app.py

Contiene la aplicación FastAPI, los modelos Pydantic y las rutas HTTP.

### GET /health

Comprueba que la API está funcionando.

Respuesta actual:

```json
{
  "message": "ia-serverless-app funcionando",
  "environment": "dev"
}
```

El entorno no está hardcodeado. Se obtiene con:

```python
os.getenv("ENVIRONMENT", "unknown")
```

Terraform configura `ENVIRONMENT` utilizando `var.environment`.

### POST /api/chat

Primera ruta funcional del backend.

Entrada:

```json
{
  "message": "Hola desde FastAPI"
}
```

Salida:

```json
{
  "response": "Mensaje recibido: Hola desde FastAPI",
  "environment": "dev"
}
```

Por ahora esta ruta **no utiliza IA**. Devuelve una respuesta controlada para validar primero el flujo completo de la API antes de introducir Bedrock o RAG.

El contrato está tipado mediante Pydantic:

```python
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    environment: str
```

Esto permite que FastAPI valide automáticamente la estructura de entrada y salida.

## lambda_function.py

Es el punto de entrada de AWS Lambda y conecta Lambda con FastAPI mediante Mangum:

```python
from mangum import Mangum
from app import app

lambda_handler = Mangum(app)
```

La lógica HTTP permanece en FastAPI y `lambda_function.py` actúa únicamente como adaptador.

## requirements.txt

Dependencias directas:

```text
fastapi==0.141.1
mangum==0.22.0
```

Las dependencias transitivas, como Pydantic o Starlette, son resueltas automáticamente por `pip`.

## Entorno virtual

El entorno virtual se crea desde la **raíz del proyecto**:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python --version
pip install -r backend/requirements.txt
```

Debe utilizar Python 3.12.

El directorio `.venv/` es local y no se versiona en Git.

## Build para AWS Lambda

El proyecto dispone de:

```text
scripts/build_lambda.sh
```

Se ejecuta desde la **raíz del proyecto**:

```bash
./scripts/build_lambda.sh
```

El script:

1. limpia el build anterior;
2. crea `build/lambda/`;
3. instala las dependencias para **Python 3.12 / Linux x86_64**;
4. copia `app.py`;
5. copia `lambda_function.py`.

El resultado es similar a:

```text
build/lambda/
├── app.py
├── lambda_function.py
├── fastapi/
├── mangum/
├── pydantic/
├── pydantic_core/
├── starlette/
└── ...
```

`build/` es generado automáticamente y no se versiona en Git.

Terraform comprime este directorio para crear el paquete ZIP desplegado en AWS Lambda.

## ¿Cuándo ejecutar build_lambda.sh?

Debe volver a ejecutarse antes de `terraform plan` cuando cambie alguno de estos archivos:

```text
backend/app.py
backend/lambda_function.py
backend/requirements.txt
```

Flujo:

```text
Cambiar backend
      |
      v
./scripts/build_lambda.sh
      |
      v
build/lambda/
      |
      v
Terraform
      |
      v
AWS Lambda
```

Es importante ejecutar el build **antes de `terraform plan`**, porque Terraform empaqueta el contenido existente en `build/lambda/`.

## API Gateway

Actualmente API Gateway expone dos rutas:

```text
GET  /health
POST /api/chat
```

Ambas utilizan la misma integración con la misma Lambda.

La ruta de chat está definida en Terraform mediante un recurso equivalente a:

```hcl
resource "aws_apigatewayv2_route" "chat" {
  api_id = aws_apigatewayv2_api.api.id

  route_key = "POST /api/chat"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}
```

FastAPI decide después qué función debe ejecutar en función del método HTTP y la ruta recibida.

## Onboarding

Después de clonar el repositorio:

```bash
# Desde la raíz de ia-serverless-app

python3.12 -m venv .venv
source .venv/bin/activate

pip install -r backend/requirements.txt

./scripts/build_lambda.sh

cd infrastructure/terraform

terraform init
terraform validate
terraform plan
```

Antes de ejecutar:

```bash
terraform apply
```

se debe revisar siempre:

```text
recursos que se crean
recursos que se modifican
recursos que se destruyen
posible impacto económico
```

La autenticación y configuración AWS/Terraform se documentan en la documentación de infraestructura.

## Último despliegue validado

Para incorporar `POST /api/chat`, el plan de Terraform mostró:

```text
Plan: 1 to add, 1 to change, 0 to destroy.
```

Los cambios fueron:

```text
+ nueva ruta POST /api/chat en API Gateway
~ actualización del código de la Lambda
```

No se creó una nueva Lambda ni infraestructura persistente adicional.

## Pruebas realizadas

### Health check

```text
GET /health
```

Continúa funcionando correctamente después del despliegue.

### Chat

Prueba realizada:

```bash
curl -X POST   https://h9lsg64yy3.execute-api.eu-west-1.amazonaws.com/api/chat   -H "Content-Type: application/json"   -d '{"message":"Hola desde FastAPI"}'
```

Respuesta obtenida:

```json
{
  "response": "Mensaje recibido: Hola desde FastAPI",
  "environment": "dev"
}
```

Con esta prueba se ha validado el recorrido completo:

```text
API Gateway
      |
      v
Lambda
      |
      v
Mangum
      |
      v
FastAPI
      |
      v
Pydantic
      |
      v
Respuesta HTTP
```

## Estado del Capítulo 2

Hasta este punto se ha completado:

- creación de la aplicación FastAPI;
- mantenimiento del contrato existente de `/health`;
- integración FastAPI ↔ Lambda mediante Mangum;
- alineación del entorno local con Python 3.12;
- declaración de dependencias en `requirements.txt`;
- build reproducible para Linux x86_64;
- empaquetado del backend y sus dependencias;
- despliegue mediante Terraform;
- creación de `POST /api/chat`;
- validación de entrada y salida mediante Pydantic;
- nueva ruta correspondiente en API Gateway;
- prueba real satisfactoria de `GET /health`;
- prueba real satisfactoria de `POST /api/chat`.

Todavía no se ha añadido Bedrock, RAG ni ningún servicio de IA. La ruta de chat sigue siendo determinista y sirve para validar la arquitectura base antes de incorporar IA.
