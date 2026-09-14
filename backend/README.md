# Backend — ia-serverless-app

Este directorio contiene el backend de `ia-serverless-app`.

El backend se implementa con **FastAPI** y se ejecuta de forma serverless en **AWS Lambda**. **Mangum** actúa como adaptador entre API Gateway/Lambda y la aplicación ASGI.

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
            |
            v
      chat_service.py
            |
      +-----+------------------+
      |                        |
      v                        v
flujo determinista        ai_service.py
                               |
                      +--------+--------+
                      |                 |
                      v                 v
                    mock             bedrock
                                        |
                                        v
                               bedrock_client.py
                                        |
                                        v
                             Amazon Bedrock Converse
                                        |
                                        v
                               Amazon Nova Micro
```

La integración con Bedrock está activa en el entorno desplegado mediante `AI_PROVIDER=bedrock`. La ruta `POST /api/chat` está protegida por API Gateway mediante throttling y autenticación JWT con Amazon Cognito, por lo que las invocaciones reales al modelo solo se permiten tras validar un token JWT válido.

## Versiones actuales

```text
Python    3.12
FastAPI   0.141.1
Mangum    0.22.0
boto3     1.43.93
pytest    8.4.2
httpx2    2.12.0
```

AWS Lambda utiliza el runtime `python3.12`.

## Estructura

```text
backend/
├── app.py
├── lambda_function.py
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── clients/
│   ├── __init__.py
│   └── bedrock_client.py
├── services/
│   ├── __init__.py
│   ├── ai_service.py
│   └── chat_service.py
└── tests/
    ├── __init__.py
    ├── test_ai_service.py
    ├── test_bedrock_client.py
    ├── test_chat_service.py
    └── test_app.py
```

## `app.py`

Contiene la aplicación FastAPI, los modelos Pydantic y las rutas HTTP.

### `GET /health`

Respuesta esperada:

```json
{
  "message": "ia-serverless-app funcionando",
  "environment": "dev"
}
```

El entorno se obtiene con:

```python
os.getenv("ENVIRONMENT", "unknown")
```

Terraform configura `ENVIRONMENT` mediante `var.environment`.

### `POST /api/chat`

Entrada:

```json
{
  "message": "Analiza este documento"
}
```

Con `AI_PROVIDER=bedrock`, los mensajes que `chat_service.py` clasifica como consultas de IA se envían a Amazon Bedrock. Por ejemplo, una petición autenticada con `"Explica en una frase qué es AWS Lambda"` fue validada de extremo a extremo y devolvió HTTP `200` con una respuesta generada por Nova Micro.

La ruta delega en `services/chat_service.py`, que decide si la petición requiere IA.

### Validación de entrada

Estado desplegado y validado en AWS:

```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000
    )

class ChatResponse(BaseModel):
    response: str
    environment: str
```

Con esto FastAPI rechaza mensajes vacíos y mensajes de más de 4000 caracteres antes de llegar a la lógica de negocio o al proveedor de IA.

El límite de 4000 caracteres es también una medida básica de control de coste.

> Este control ya está cubierto por tests y desplegado en AWS. Se validó mediante API Gateway que un mensaje vacío devuelve HTTP `422`.

## Capa de servicios

### `chat_service.py`

Contiene la lógica específica del chat.

```text
POST /api/chat
      |
      v
chat_service.py
      |
      +--> flujo determinista
      |
      +--> ai_service.py (use_case="chat")
```

La detección inicial utiliza palabras clave como `explica`, `resume`, `analiza`, `recomienda` e `interpreta`.

### `ai_service.py`

Es la capa común y reutilizable de acceso a servicios de Inteligencia Artificial.

```python
provider = os.getenv("AI_PROVIDER", "mock")
```

Proveedores implementados:

```text
mock
bedrock
```

`mock` sigue siendo el valor por defecto y no realiza llamadas externas ni genera coste de IA.

Cuando `AI_PROVIDER=bedrock`, la capa delega en `clients/bedrock_client.py`.

## `clients/bedrock_client.py`

Cliente específico para Amazon Bedrock.

El identificador del modelo ya no está hardcodeado en Python. Se obtiene obligatoriamente desde la variable de entorno:

```python
model_id = os.environ["BEDROCK_MODEL_ID"]
```

Terraform define actualmente como valor por defecto:

```text
eu.amazon.nova-micro-v1:0
```

El primer modelo preparado es **Amazon Nova Micro** mediante el perfil europeo:

```text
eu.amazon.nova-micro-v1:0
```

La llamada utiliza `boto3` y la API `Converse`:

```python
client = boto3.client("bedrock-runtime")

response = client.converse(
    modelId=model_id,
    messages=[
        {
            "role": "user",
            "content": [{"text": message}]
        }
    ],
    inferenceConfig={
        "maxTokens": 300,
        "temperature": 0.2,
    }
)
```

### Controles de coste de inferencia

Actualmente existen dos límites complementarios:

```text
Entrada API  -> máximo 4000 caracteres
Salida LLM   -> máximo 300 tokens
```

Además, `AI_PROVIDER=mock` continúa siendo el valor seguro por defecto en `variables.tf`, aunque el entorno `dev` se ha activado explícitamente con `ai_provider = "bedrock"` en `terraform.tfvars`.

No se utiliza Provisioned Throughput ni capacidad reservada de Bedrock.

## Estado de Bedrock

Ya está preparado:

- cliente Bedrock mediante `boto3`;
- Amazon Nova Micro;
- API `Converse`;
- rama `AI_PROVIDER=bedrock`;
- tests mockeados sin llamadas AWS;
- empaquetado del directorio `clients/`;
- permisos IAM mínimos para `bedrock:InvokeModel`;
- perfil de inferencia europeo;
- despliegue del código y permisos.

El entorno desplegado se ha activado explícitamente con:

```text
AI_PROVIDER = bedrock
```

La integración ya ha sido validada desde la aplicación desplegada mediante una petición autenticada a `POST /api/chat`, con respuesta HTTP `200` generada por Amazon Nova Micro.

## `lambda_function.py`

Punto de entrada de AWS Lambda:

```python
from mangum import Mangum
from app import app

lambda_handler = Mangum(app)
```

## Dependencias

### `requirements.txt`

```text
fastapi==0.141.1
mangum==0.22.0
boto3==1.43.93
```

`boto3` se declara explícitamente para hacer reproducible la versión utilizada por `bedrock_client.py`.

### `requirements-dev.txt`

```text
-r requirements.txt

pytest==8.4.2
httpx2==2.12.0
```

Instalación:

```bash
python -m pip install -r backend/requirements-dev.txt
```

## Tests locales

Ejecución completa:

```bash
cd backend
pytest -v
```

Cobertura relevante:

```text
tests/test_ai_service.py
├── proveedor mock por defecto
├── propagación de use_case
├── error ante proveedor no soportado
└── rama bedrock mockeada

tests/test_bedrock_client.py
└── llamada Converse mockeada y modelo recibido mediante BEDROCK_MODEL_ID

tests/test_chat_service.py
├── mensaje que no requiere IA
└── mensaje que requiere IA

tests/test_app.py
├── GET /health
├── POST /api/chat sin IA
├── POST /api/chat con IA mock
├── rechazo de mensaje vacío
└── rechazo de mensaje superior a 4000 caracteres
```

Validación completa actual:

```bash
cd backend
pytest -v
```

Resultado confirmado:

```text
12 passed, 1 warning in 0.27s
```

El warning procede de una deprecación de `anyio.abc.BlockingPortal` utilizada por `starlette.testclient`; no bloquea el funcionamiento actual.

Los tests de Bedrock están mockeados, no necesitan credenciales AWS y no realizan llamadas reales al modelo.

## Entorno virtual

Desde la raíz del proyecto:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python --version
pip install -r backend/requirements-dev.txt
```

El directorio `.venv/` no se versiona.

## Build para AWS Lambda

El script es:

```text
scripts/build_lambda.sh
```

Se ejecuta desde la raíz:

```bash
./scripts/build_lambda.sh
```

El script:

1. limpia el build anterior;
2. crea `build/lambda/`;
3. instala dependencias para Python 3.12 / Linux x86_64;
4. copia `app.py`;
5. copia `lambda_function.py`;
6. copia `services/`;
7. copia `clients/`.

Resultado aproximado:

```text
build/lambda/
├── app.py
├── lambda_function.py
├── services/
│   ├── __init__.py
│   ├── ai_service.py
│   └── chat_service.py
├── clients/
│   ├── __init__.py
│   └── bedrock_client.py
├── boto3/
├── botocore/
├── fastapi/
├── mangum/
└── ...
```

`build/` es generado automáticamente y no se versiona.

Debe ejecutarse de nuevo antes de `terraform plan` cuando cambien:

```text
backend/app.py
backend/lambda_function.py
backend/requirements.txt
backend/services/*.py
backend/clients/*.py
```

## API Gateway

Rutas actuales:

```text
GET  /health
POST /api/chat
```

Ambas utilizan la misma Lambda.

## IAM para Bedrock

La Lambda dispone ya de una policy específica para Bedrock con enfoque least privilege.

Permiso:

```text
bedrock:InvokeModel
```

Se aplica al perfil de inferencia europeo de Nova Micro y a los foundation models asociados.

El account ID no se hardcodea. Terraform lo obtiene mediante:

```hcl
data "aws_caller_identity" "current" {}
```

Esto mantiene la infraestructura portable entre cuentas AWS.

Añadir la policy IAM no genera consumo de Bedrock por sí mismo.

## Flujo de desarrollo recomendado

```text
cambio backend
      |
      v
pytest local
      |
      v
build_lambda.sh
      |
      v
terraform validate
      |
      v
terraform plan
      |
      v
revisión de cambios y coste
      |
      v
terraform apply
      |
      v
prueba E2E AWS
```

Antes de cada `apply` hay que revisar siempre los recursos que se crean, modifican o destruyen y su posible impacto económico.

## Último despliegue validado

Para activar Bedrock en el entorno `dev`, Terraform mostró:

```text
Plan: 0 to add, 1 to change, 0 to destroy.
```

El único cambio fue una actualización **in-place** de la Lambda:

```text
~ aws_lambda_function.api
```

con el cambio de variable de entorno:

```text
AI_PROVIDER = mock -> bedrock
```

El apply terminó con:

```text
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

No se creó ni destruyó ningún recurso. Después del despliegue se ejecutó una petición autenticada a `POST /api/chat` con el mensaje `Explica en una frase qué es AWS Lambda`. API Gateway validó el JWT de Cognito y la aplicación devolvió HTTP `200` con una respuesta real de Amazon Nova Micro.

## Primera invocación real a Amazon Bedrock

Se ha realizado con éxito la primera llamada real y controlada a Amazon Bedrock desde el entorno local de desarrollo.

La prueba se ejecutó desde `backend/` usando el perfil SSO del proyecto y la región `eu-west-1`:

```bash
AWS_PROFILE=ia-serverless-dev \
AWS_DEFAULT_REGION=eu-west-1 \
BEDROCK_MODEL_ID=eu.amazon.nova-micro-v1:0 \
python -c '\
from clients.bedrock_client import generate_text\
print(generate_text("Responde únicamente con: Bedrock funciona", "test"))\
'
```

Respuesta obtenida:

```text
Bedrock funciona.
```

Esta prueba confirma que funcionan conjuntamente:

```text
AWS SSO / STS
   |
   v
boto3 bedrock-runtime
   |
   v
Converse API
   |
   v
eu.amazon.nova-micro-v1:0
   |
   v
Amazon Nova Micro
```

La primera invocación fue deliberadamente local y puntual. Después se añadieron dos barreras frente a consumo no deseado: throttling y autenticación JWT con Amazon Cognito. Una vez validadas, se activó `AI_PROVIDER=bedrock` en la Lambda de `dev` y se completó también una llamada real E2E desde `POST /api/chat`. `GET /health` continúa público, mientras que `POST /api/chat` exige un JWT válido.

## Control de costes

Medidas actuales:

- `AI_PROVIDER=mock` como valor seguro por defecto en Terraform;
- activación explícita de `bedrock` solo en el entorno `dev`;
- Nova Micro como primer modelo;
- `maxTokens=300`;
- entrada limitada a 4000 caracteres;
- IAM específico para `bedrock:InvokeModel`;
- sin Provisioned Throughput;
- tests mockeados sin consumo AWS;
- revisión de `terraform plan` antes de cada `apply`.

## Portabilidad

El diseño evita acoplarse a una cuenta AWS concreta:

- account ID obtenido dinámicamente;
- región configurada mediante variables Terraform;
- dependencias Python versionadas;
- build reproducible para Python 3.12/Linux x86_64;
- proveedor IA seleccionado mediante `AI_PROVIDER`.

La selección del modelo Bedrock ya está externalizada completamente: Terraform define `bedrock_model_id`, Lambda recibe `BEDROCK_MODEL_ID` y Python exige esa variable mediante `os.environ` sin fallback silencioso.

## Estado actual

Completado:

- FastAPI sobre Lambda mediante Mangum;
- `/health` y `/api/chat`;
- capa `services/`;
- `chat_service.py`;
- `ai_service.py`;
- proveedor `mock`;
- proveedor `bedrock`;
- `clients/bedrock_client.py`;
- Amazon Nova Micro preparado;
- Bedrock Converse preparado;
- `boto3` versionado;
- tests Bedrock mockeados;
- build actualizado con `clients/`;
- IAM least privilege para Bedrock;
- despliegue satisfactorio;
- E2E autenticado validado con `AI_PROVIDER=bedrock`;
- primera invocación real a Amazon Bedrock validada desde local y desde la API protegida;
- límite de entrada de 1 a 4000 caracteres probado y desplegado;
- respuesta HTTP 422 validada para mensaje vacío;
- full suite validado con 12 tests;
- `BEDROCK_MODEL_ID` externalizado a Terraform/Lambda;
- límite de salida de 300 tokens.

Primera llamada real a Bedrock: completada correctamente desde local y desde la API protegida.

Estado operativo actual:

```text
AI_PROVIDER=bedrock en dev
JWT Cognito obligatorio en POST /api/chat
throttling 2 req/s, burst 5
entrada máxima 4000 caracteres
salida máxima 300 tokens
```

Cuando se detenga temporalmente el desarrollo, `AI_PROVIDER` debe volver a `mock` para evitar consumo accidental.

RAG todavía no se ha incorporado. Se añadirá en una fase posterior.

## Protección del endpoint con throttling

La ruta pública `POST /api/chat` está protegida mediante throttling en API Gateway antes de llegar a Lambda.

Configuración desplegada:

```text
Rate limit: 2 peticiones/segundo
Burst limit: 5 peticiones
```

El control se aplica en API Gateway, por lo que las peticiones rechazadas no continúan hacia Lambda ni hacia Lambda/Bedrock.

`GET /health` no tiene este límite específico.

### Validación de integración

Se realizó una prueba real contra la API pública con `AI_PROVIDER=mock`, enviando 100 peticiones con concurrencia 25.

Resultado de la validación final:

```text
42 200
58 429
```

Esto confirma que API Gateway devuelve `HTTP 429 Too Many Requests` cuando el tráfico supera el límite efectivo.

Una prueba anterior produjo:

```text
66 200
18 429
16 503
```

La segunda ejecución validó de forma limpia el comportamiento esperado del throttling mediante respuestas `429`.

> El throttling de API Gateway es un control de tasa y ráfaga, no un límite presupuestario rígido. La autenticación se resuelve ahora con un authorizer JWT de API Gateway conectado a Amazon Cognito. `AI_PROVIDER` está actualmente en `bedrock` en el entorno `dev`.


## Autenticación con Amazon Cognito

La ruta `POST /api/chat` está protegida mediante un **JWT authorizer** de API Gateway conectado a un **Amazon Cognito User Pool**. La autenticación ocurre antes de invocar la Lambda, por lo que una petición sin token válido no alcanza FastAPI ni puede provocar una futura llamada a Bedrock.

Comportamiento validado en AWS:

```text
GET  /health sin token       -> 200 OK
POST /api/chat sin token     -> 401 Unauthorized
POST /api/chat con JWT válido -> 200 OK
```

Prueba autenticada confirmada:

```json
{
  "response": "Mensaje recibido: Hola",
  "environment": "dev"
}
```

El JWT se obtiene mediante Cognito y se envía como:

```text
Authorization: Bearer <JWT>
```

Actualmente la autenticación se valida en API Gateway; no ha sido necesario modificar el código FastAPI para bloquear las peticiones anónimas. Esto mantiene separadas las responsabilidades:

```text
Cognito        -> autentica al usuario
API Gateway    -> valida el JWT y aplica throttling
Lambda/FastAPI -> ejecuta la lógica de negocio
```

Durante la validación inicial de Cognito el entorno todavía estaba en `mock`, por lo que esas pruebas de autenticación no generaron consumo de Bedrock. Posteriormente se activó `bedrock` y se validó una petición autenticada real con HTTP `200`.
