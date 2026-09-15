# Backend --- ia-serverless-app

Este directorio contiene el backend de `ia-serverless-app`.

El backend se implementa con **FastAPI** y se ejecuta de forma
serverless en **AWS Lambda**. **Mangum** actúa como adaptador entre API
Gateway/Lambda y la aplicación ASGI.

## Arquitectura actual

``` text
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
   +--> POST /api/documents/upload-url
   |
   +--> GET /api/refrigeration/status
   |
   +--> GET /api/tachograph/status
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

La integración con Bedrock está preparada y ya fue validada, pero el
entorno desplegado utiliza actualmente `AI_PROVIDER=mock` para evitar
consumo accidental. La ruta `POST /api/chat` continúa protegida por API
Gateway mediante throttling y autenticación JWT con Amazon Cognito.

## Versiones actuales

``` text
Python    3.12
FastAPI   0.141.1
Mangum    0.22.0
boto3     1.43.93
pytest    8.4.2
httpx2    2.12.0
```

AWS Lambda utiliza el runtime `python3.12`.

## Estructura

``` text
backend/
├── app.py
├── lambda_function.py
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── clients/
│   ├── __init__.py
│   └── bedrock_client.py
├── integrations/
│   ├── refrigeration_source.py
│   └── tachograph_source.py
├── mocks/
│   ├── refrigeration_data.json
│   └── tachograph_data.json
├── services/
│   ├── __init__.py
│   ├── ai_service.py
│   ├── chat_service.py
│   ├── document_service.py
│   ├── refrigeration_service.py
│   └── tachograph_service.py
└── tests/
    ├── __init__.py
    ├── test_ai_service.py
    ├── test_bedrock_client.py
    ├── test_chat_service.py
    ├── test_document_service.py
    ├── test_refrigeration_service.py
    ├── test_tachograph_service.py
    └── test_app.py
```

## `app.py`

Contiene la aplicación FastAPI, los modelos Pydantic y las rutas HTTP.

### `GET /health`

Respuesta esperada:

``` json
{
  "message": "ia-serverless-app funcionando",
  "environment": "dev"
}
```

El entorno se obtiene con:

``` python
os.getenv("ENVIRONMENT", "unknown")
```

Terraform configura `ENVIRONMENT` mediante `var.environment`.

### `POST /api/chat`

Entrada:

``` json
{
  "message": "Analiza este documento"
}
```

Con `AI_PROVIDER=bedrock`, los mensajes que `chat_service.py` clasifica
como consultas de IA se envían a Amazon Bedrock. Por ejemplo, una
petición autenticada con `"Explica en una frase qué es AWS Lambda"` fue
validada de extremo a extremo y devolvió HTTP `200` con una respuesta
generada por Nova Micro.

La ruta delega en `services/chat_service.py`, que decide si la petición
requiere IA.

### `GET /api/refrigeration/status`

Devuelve el estado de los dispositivos de refrigeración utilizando
`services/refrigeration_service.py`.

La ruta está protegida por Cognito JWT en API Gateway.

Estados actuales:

``` text
NORMAL
WARNING
CRITICAL
OFFLINE
```

La validación E2E realizada fue:

``` text
sin JWT        -> 401 Unauthorized
con JWT válido -> 200 OK
```

### `GET /api/tachograph/status`

Devuelve el estado de los conductores/vehículos a partir de
`services/tachograph_service.py`.

La ruta está protegida por Cognito JWT y utiliza throttling específico
en API Gateway.

Estados actuales:

``` text
NORMAL
WARNING
CRITICAL
OFFLINE
```

Validación E2E:

``` text
sin JWT        -> 401 Unauthorized
con JWT válido -> 200 OK
```

### Validación de entrada

Estado desplegado y validado en AWS:

``` python
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

Con esto FastAPI rechaza mensajes vacíos y mensajes de más de 4000
caracteres antes de llegar a la lógica de negocio o al proveedor de IA.

El límite de 4000 caracteres es también una medida básica de control de
coste.

> Este control ya está cubierto por tests y desplegado en AWS. Se validó
> mediante API Gateway que un mensaje vacío devuelve HTTP `422`.

## Capa de servicios

### `chat_service.py`

Contiene la lógica específica del chat.

``` text
POST /api/chat
      |
      v
chat_service.py
      |
      +--> flujo determinista
      |
      +--> ai_service.py (use_case="chat")
```

La detección inicial utiliza palabras clave como `explica`, `resume`,
`analiza`, `recomienda` e `interpreta`.

### `ai_service.py`

Es la capa común y reutilizable de acceso a servicios de Inteligencia
Artificial.

``` python
provider = os.getenv("AI_PROVIDER", "mock")
```

Proveedores implementados:

``` text
mock
bedrock
```

`mock` sigue siendo el valor por defecto y no realiza llamadas externas
ni genera coste de IA.

Cuando `AI_PROVIDER=bedrock`, la capa delega en
`clients/bedrock_client.py`. Con `mock`, devuelve una respuesta simulada
sin llamadas externas.

## Servicios de dominio

### Refrigeración

La integración se separa en dos capas:

``` text
refrigeration_source.py
        |
        v
refrigeration_service.py
```

`refrigeration_source.py` obtiene los datos desde la fuente configurada
mediante:

``` text
REFRIGERATION_SOURCE
```

El valor seguro por defecto es `mock`. El mock se carga desde:

``` text
mocks/refrigeration_data.json
```

La rama `api` está preparada para una futura integración externa y
actualmente no está implementada.

`refrigeration_service.py` aplica reglas deterministas y clasifica cada
lectura como:

``` text
NORMAL
WARNING
CRITICAL
OFFLINE
```

Los umbrales actuales son únicamente valores de demostración:

``` text
warning  = 7.0 °C
critical = 20.0 °C
```

No son límites regulatorios definitivos.

### Tacógrafos

El servicio de tacógrafos sigue el mismo patrón:

``` text
tachograph_source.py
        |
        v
tachograph_service.py
```

La fuente se selecciona mediante:

``` text
TACHOGRAPH_SOURCE
```

El valor seguro por defecto es:

``` text
mock
```

Los datos de prueba se encuentran en:

``` text
mocks/tachograph_data.json
```

La rama `api` está reservada para la futura integración con una fuente
externa y actualmente lanza `NotImplementedError`.

La clasificación actual utiliza reglas deterministas:

``` text
NORMAL
WARNING
CRITICAL
OFFLINE
```

Umbrales de demostración:

``` text
warning  = 480 minutos
critical = 540 minutos
```

Estos valores sirven para validar arquitectura y flujo. No representan
una implementación completa de la normativa real de tacógrafos.

La IA no interviene en ninguna de estas clasificaciones. Bedrock solo se
utilizará donde aporte valor adicional, por ejemplo para explicación,
resumen o asistencia sobre datos ya validados por reglas de negocio.

## `clients/bedrock_client.py`

Cliente específico para Amazon Bedrock.

El identificador del modelo ya no está hardcodeado en Python. Se obtiene
obligatoriamente desde la variable de entorno:

``` python
model_id = os.environ["BEDROCK_MODEL_ID"]
```

Terraform define actualmente como valor por defecto:

``` text
eu.amazon.nova-micro-v1:0
```

El primer modelo preparado es **Amazon Nova Micro** mediante el perfil
europeo:

``` text
eu.amazon.nova-micro-v1:0
```

La llamada utiliza `boto3` y la API `Converse`:

``` python
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

``` text
Entrada API  -> máximo 4000 caracteres
Salida LLM   -> máximo 300 tokens
```

Además, `AI_PROVIDER=mock` continúa siendo el valor seguro por defecto
en `variables.tf`, y el entorno `dev` ha vuelto explícitamente a
`ai_provider = "mock"` en `terraform.tfvars` tras las pruebas
controladas con Bedrock.

No se utiliza Provisioned Throughput ni capacidad reservada de Bedrock.

## Estado de Bedrock

La integración con Amazon Bedrock está implementada y fue validada tanto
desde local como desde la API protegida.

El modelo preparado es:

``` text
Amazon Nova Micro
eu.amazon.nova-micro-v1:0
```

Actualmente el backend desplegado utiliza:

``` text
AI_PROVIDER=mock
```

Esto evita invocaciones accidentales mientras se continúa desarrollando
el dominio. Para volver a utilizar Bedrock se requiere una activación
explícita y controlada.

La salida del modelo continúa limitada a:

``` text
maxTokens = 300
```

y la entrada de chat a un máximo de 4000 caracteres.

## `lambda_function.py`

Punto de entrada de AWS Lambda:

``` python
from mangum import Mangum
from app import app

lambda_handler = Mangum(app)
```

## Dependencias

### `requirements.txt`

``` text
fastapi==0.141.1
mangum==0.22.0
boto3==1.43.93
```

`boto3` se declara explícitamente para hacer reproducible la versión
utilizada por `bedrock_client.py`.

### `requirements-dev.txt`

``` text
-r requirements.txt

pytest==8.4.2
httpx2==2.12.0
```

Instalación:

``` bash
python -m pip install -r backend/requirements-dev.txt
```

## Tests locales

Ejecución completa:

``` bash
cd backend
pytest -v
```

Cobertura relevante:

``` text
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

``` bash
cd backend
pytest -v
```

Resultado confirmado:

``` text
37 passed, 1 warning
```

El warning procede de una deprecación de `anyio.abc.BlockingPortal`
utilizada por `starlette.testclient`; no bloquea el funcionamiento
actual.

Los tests de Bedrock están mockeados, no necesitan credenciales AWS y no
realizan llamadas reales al modelo.

## Entorno virtual

Desde la raíz del proyecto:

``` bash
python3.12 -m venv .venv
source .venv/bin/activate
python --version
pip install -r backend/requirements-dev.txt
```

El directorio `.venv/` no se versiona.

## Build para AWS Lambda

El script es:

``` text
scripts/build_lambda.sh
```

Se ejecuta desde la raíz:

``` bash
./scripts/build_lambda.sh
```

El script:

1.  limpia el build anterior;
2.  crea `build/lambda/`;
3.  instala dependencias para Python 3.12 / Linux x86_64;
4.  copia `app.py`;
5.  copia `lambda_function.py`;
6.  copia `services/`;
7.  copia `clients/`.

Resultado aproximado:

``` text
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

``` text
backend/app.py
backend/lambda_function.py
backend/requirements.txt
backend/services/*.py
backend/clients/*.py
```

El script de build copia también las carpetas de integración y mocks:

``` bash
cp -R "$BACKEND_DIR/integrations" "$BUILD_DIR/"
cp -R "$BACKEND_DIR/mocks" "$BUILD_DIR/"
```

Esto garantiza que las fuentes y datos mock de refrigeración y
tacógrafos estén incluidos en el ZIP de Lambda.

## API Gateway

La Lambda está integrada con una API Gateway HTTP API mediante
`AWS_PROXY`.

Rutas actuales:

``` text
GET  /health
POST /api/chat
POST /api/documents/upload-url
GET  /api/refrigeration/status
GET  /api/tachograph/status
```

Protección:

``` text
GET  /health                       -> pública
POST /api/chat                     -> JWT Cognito + throttling
POST /api/documents/upload-url     -> JWT Cognito + throttling
GET  /api/refrigeration/status     -> JWT Cognito + throttling 2 req/s, burst 5
GET  /api/tachograph/status        -> JWT Cognito + throttling 2 req/s, burst 5
```

Las rutas de refrigeración y tacógrafos se validaron de extremo a
extremo con:

``` text
sin JWT        -> 401 Unauthorized
con JWT válido -> 200 OK
```

## IAM para Bedrock

La Lambda dispone ya de una policy específica para Bedrock con enfoque
least privilege.

Permiso:

``` text
bedrock:InvokeModel
```

Se aplica al perfil de inferencia europeo de Nova Micro y a los
foundation models asociados.

El account ID no se hardcodea. Terraform lo obtiene mediante:

``` hcl
data "aws_caller_identity" "current" {}
```

Esto mantiene la infraestructura portable entre cuentas AWS.

Añadir la policy IAM no genera consumo de Bedrock por sí mismo.

## Flujo de desarrollo recomendado

``` text
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

Antes de cada `apply` hay que revisar siempre los recursos que se crean,
modifican o destruyen y su posible impacto económico.

## Último despliegue validado

El último bloque desplegado corresponde al servicio de tacógrafos.

Primero se creó la ruta protegida y se actualizó el throttling:

``` text
Plan: 1 to add, 1 to change, 0 to destroy.
Apply complete! Resources: 1 added, 1 changed, 0 destroyed.
```

Después se reconstruyó el ZIP de Lambda y Terraform detectó únicamente
el cambio de código:

``` text
Plan: 0 to add, 1 to change, 0 to destroy.
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

Validación E2E:

``` text
GET /api/tachograph/status sin JWT        -> 401 Unauthorized
GET /api/tachograph/status con JWT válido -> 200 OK
```

La respuesta validada contiene:

``` text
DRIVER-001 -> NORMAL
DRIVER-002 -> WARNING
DRIVER-003 -> CRITICAL
DRIVER-004 -> OFFLINE
```

## Primera invocación real a Amazon Bedrock

Se ha realizado con éxito la primera llamada real y controlada a Amazon
Bedrock desde el entorno local de desarrollo.

La prueba se ejecutó desde `backend/` usando el perfil SSO del proyecto
y la región `eu-west-1`:

``` bash
AWS_PROFILE=ia-serverless-dev \
AWS_DEFAULT_REGION=eu-west-1 \
BEDROCK_MODEL_ID=eu.amazon.nova-micro-v1:0 \
python -c '\
from clients.bedrock_client import generate_text\
print(generate_text("Responde únicamente con: Bedrock funciona", "test"))\
'
```

Respuesta obtenida:

``` text
Bedrock funciona.
```

Esta prueba confirma que funcionan conjuntamente:

``` text
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

La primera invocación fue deliberadamente local y puntual. Después se
añadieron dos barreras frente a consumo no deseado: throttling y
autenticación JWT con Amazon Cognito. Una vez validadas, se activó
`AI_PROVIDER=mock` en la Lambda de `dev` y se completó también una
llamada real E2E desde `POST /api/chat`. `GET /health` continúa público,
mientras que `POST /api/chat` exige un JWT válido.

## Control de costes

Medidas actuales:

-   `AI_PROVIDER=mock` como valor seguro por defecto en Terraform;
-   activación explícita y temporal de `bedrock` solo para pruebas
    controladas; estado final de `dev`: `mock`;
-   Nova Micro como primer modelo;
-   `maxTokens=300`;
-   entrada limitada a 4000 caracteres;
-   IAM específico para `bedrock:InvokeModel`;
-   sin Provisioned Throughput;
-   tests mockeados sin consumo AWS;
-   revisión de `terraform plan` antes de cada `apply`.

## Portabilidad

El diseño evita acoplarse a una cuenta AWS concreta:

-   account ID obtenido dinámicamente;
-   región configurada mediante variables Terraform;
-   dependencias Python versionadas;
-   build reproducible para Python 3.12/Linux x86_64;
-   proveedor IA seleccionado mediante `AI_PROVIDER`.

La selección del modelo Bedrock ya está externalizada completamente:
Terraform define `bedrock_model_id`, Lambda recibe `BEDROCK_MODEL_ID` y
Python exige esa variable mediante `os.environ` sin fallback silencioso.

## Estado actual

``` text
API Gateway HTTP API
   |
   +--> GET /health
   |
   +--> POST /api/chat
   |
   +--> POST /api/documents/upload-url
   |
   +--> GET /api/refrigeration/status
   |
   +--> GET /api/tachograph/status
            |
            v
         Lambda
            |
            v
     FastAPI + Mangum
            |
     +------+----------------------+--------------------+
     |                             |                    |
     v                             v                    v
chat_service              refrigeration_service  tachograph_service
     |                             |                    |
     v                             v                    v
ai_service              refrigeration_source   tachograph_source
   /   \                        mock/API             mock/API
 mock  bedrock
  ↑
 mock activo; Bedrock preparado
```

Estado efectivo del proveedor de IA:

``` text
AI_PROVIDER=mock
```

Bedrock permanece implementado y validado, pero no se invoca mientras
`AI_PROVIDER=mock`.

La suite completa:

``` text
37 passed, 1 warning
```

## Protección del endpoint con throttling

La ruta pública `POST /api/chat` está protegida mediante throttling en
API Gateway antes de llegar a Lambda.

Configuración desplegada:

``` text
Rate limit: 2 peticiones/segundo
Burst limit: 5 peticiones
```

El control se aplica en API Gateway, por lo que las peticiones
rechazadas no continúan hacia Lambda ni hacia Lambda/Bedrock.

`GET /health` no tiene este límite específico.

### Validación de integración

Se realizó una prueba real contra la API pública con `AI_PROVIDER=mock`,
enviando 100 peticiones con concurrencia 25.

Resultado de la validación final:

``` text
42 200
58 429
```

Esto confirma que API Gateway devuelve `HTTP 429 Too Many Requests`
cuando el tráfico supera el límite efectivo.

Una prueba anterior produjo:

``` text
66 200
18 429
16 503
```

La segunda ejecución validó de forma limpia el comportamiento esperado
del throttling mediante respuestas `429`.

> El throttling de API Gateway es un control de tasa y ráfaga, no un
> límite presupuestario rígido. La autenticación se resuelve ahora con
> un authorizer JWT de API Gateway conectado a Amazon Cognito.
> `AI_PROVIDER` está actualmente en `mock` en el entorno `dev`.

## Autenticación con Amazon Cognito

La ruta `POST /api/chat` está protegida mediante un **JWT authorizer**
de API Gateway conectado a un **Amazon Cognito User Pool**. La
autenticación ocurre antes de invocar la Lambda, por lo que una petición
sin token válido no alcanza FastAPI ni puede provocar una futura llamada
a Bedrock.

Comportamiento validado en AWS:

``` text
GET  /health sin token       -> 200 OK
POST /api/chat sin token     -> 401 Unauthorized
POST /api/chat con JWT válido -> 200 OK
```

Prueba autenticada confirmada:

``` json
{
  "response": "Mensaje recibido: Hola",
  "environment": "dev"
}
```

El JWT se obtiene mediante Cognito y se envía como:

``` text
Authorization: Bearer <JWT>
```

Actualmente la autenticación se valida en API Gateway; no ha sido
necesario modificar el código FastAPI para bloquear las peticiones
anónimas. Esto mantiene separadas las responsabilidades:

``` text
Cognito        -> autentica al usuario
API Gateway    -> valida el JWT y aplica throttling
Lambda/FastAPI -> ejecuta la lógica de negocio
```

Durante la validación inicial de Cognito el entorno todavía estaba en
`mock`, por lo que esas pruebas de autenticación no generaron consumo de
Bedrock. Posteriormente se activó `bedrock` y se validó una petición
autenticada real con HTTP `200`.

------------------------------------------------------------------------

## Ingesta documental: subida segura a S3

Se ha completado la primera fase de la ingesta documental para RAG:
generación de autorizaciones temporales para que el cliente suba
documentos directamente a Amazon S3 sin transportar el archivo a través
de API Gateway y Lambda.

### Endpoint

``` text
POST /api/documents/upload-url
```

La ruta está protegida mediante JWT de Amazon Cognito. API Gateway
valida el token antes de invocar la Lambda.

El backend extrae el `sub` del usuario autenticado y genera una clave S3
controlada por el servidor:

``` text
uploads/<user_id>/<uuid>.<extension>
```

El nombre original enviado por el cliente no se utiliza como clave S3.

### Formatos y validación

Formatos iniciales:

``` text
PDF -> application/pdf
TXT -> text/plain
```

Los controles configurables incluyen:

``` text
Tamaño máximo por archivo: 20 MB
Máximo de páginas PDF: 100
Máximo de archivos por lote: 10
Máximo de chunks por documento: 500
Extensiones permitidas: pdf, txt
```

En esta fase se aplican ya la validación de extensión, `Content-Type`,
tamaño declarado y tamaño real de la subida. Los límites de páginas,
lotes y chunks se aplicarán en el worker de ingesta antes de operaciones
potencialmente más costosas como OCR, embeddings o indexación vectorial.

El worker deberá volver a inspeccionar el contenido real del fichero; no
se confiará únicamente en el `Content-Type` proporcionado por el
cliente.

### Presigned POST

Se utiliza una presigned POST de S3 con una validez de:

``` text
300 segundos
```

La política incluye:

``` text
content-length-range
```

por lo que S3 puede rechazar directamente un cuerpo que supere el límite
configurado, incluso si el cliente declara otro tamaño al backend.

El cliente S3 se configura con la región de ejecución (`AWS_REGION`) y
genera directamente un endpoint regional. Esto corrigió el
`307 Temporary Redirect` observado en la primera prueba con el endpoint
global.

La validación E2E posterior obtuvo directamente:

``` text
HTTP/1.1 204 No Content
```

sin utilizar `curl -L`.

S3 confirmó además:

``` text
x-amz-server-side-encryption: AES256
```

### IAM

La Lambda API dispone únicamente de `s3:PutObject` sobre:

``` text
<documents-bucket>/uploads/*
```

No dispone de permisos generales `s3:*`, ni de lectura, borrado o
listado del bucket para esta funcionalidad.

### Throttling

El endpoint de generación de URLs de subida tiene throttling específico
en API Gateway:

``` text
Rate limit: 1 petición/segundo
Burst limit: 2 peticiones
```

Este control reduce ráfagas y abuso accidental antes de llegar a Lambda.
No constituye un límite presupuestario absoluto.

### Tests

La suite actual del backend valida también la lógica documental y el
endpoint HTTP, incluyendo la generación de la presigned POST, límites de
tamaño, extensiones, MIME, autenticación y configuración regional de S3.

Resultado actual:

``` text
37 passed, 1 warning
```

El warning procede de una deprecación de Starlette/AnyIO y no bloquea la
ejecución.

### Próximo bloque

La siguiente fase prevista del pipeline RAG es:

``` text
S3
 ↓
SQS
 ↓
Lambda worker de ingesta
 ↓
extracción / validación
 ↓
chunking
 ↓
embeddings
 ↓
índice vectorial
```

Antes de incorporar OpenSearch u otra infraestructura vectorial se
revisará explícitamente su modalidad de coste.

## Validación del servicio de tacógrafos

Pruebas locales específicas:

``` text
4 passed
```

Prueba del endpoint FastAPI:

``` text
1 passed, 1 warning
```

Suite completa después de incorporar el módulo:

``` text
37 passed, 1 warning
```

Prueba real en AWS:

``` text
GET /api/tachograph/status sin JWT        -> 401 Unauthorized
GET /api/tachograph/status con JWT válido -> 200 OK
```

El módulo reutiliza la Lambda, API Gateway y Cognito existentes. No se
ha añadido una Lambda adicional ni infraestructura siempre encendida.

------------------------------------------------------------------------

## Integración IA de refrigeración y tacógrafos

Se ha completado la integración de los dos servicios de dominio con
`ai_service.py`, manteniendo separadas las **reglas deterministas** y el
**análisis generativo**.

### Separación `/status` y `/analysis`

Los endpoints `GET /api/refrigeration/status` y
`GET /api/tachograph/status` no invocan IA. Devuelven las
clasificaciones `NORMAL`, `WARNING`, `CRITICAL` y `OFFLINE` calculadas
por reglas de negocio.

Los nuevos endpoints `GET /api/refrigeration/analysis` y
`GET /api/tachograph/analysis` reciben esos datos ya clasificados y
delegan el análisis en `ai_service.py`. Así, una consulta ordinaria de
estado no consume Bedrock.

### Grounding y reducción de alucinaciones

Las clasificaciones son autoridad del backend. El modelo no debe
cambiarlas, traducirlas, recalcularlas ni cuestionarlas.

En refrigeración se prohíbe inferir averías, daños en mercancía o
alimentos, pérdidas de producto, riesgos sanitarios, consecuencias
económicas o límites regulatorios no proporcionados.

En tacógrafos se prohíbe interpretar los valores como prueba de
cumplimiento o incumplimiento legal, inventar límites legales o
describir valores como `permitido`, `máximo legal`, `ilegal`, `excedido`
o `incumplido`.

Los prompts incorporan además este contrato de interpretación:

``` text
NORMAL   -> clasificación interna; sin acción prioritaria por esa clasificación
WARNING  -> revisión o seguimiento
CRITICAL -> revisión prioritaria o inmediata
OFFLINE  -> comprobar disponibilidad/conectividad de la fuente
```

Las primeras pruebas reales con Bedrock mostraron inferencias no
respaldadas, por lo que se endurecieron los prompts. El prompting reduce
el riesgo, pero para flujos de alta criticidad deberá añadirse
validación de salida en código.

### Throttling

``` text
GET /api/refrigeration/status   -> 2 req/s, burst 5
GET /api/tachograph/status      -> 2 req/s, burst 5
GET /api/refrigeration/analysis -> 1 req/s, burst 2
GET /api/tachograph/analysis    -> 1 req/s, burst 2
```

### Tests y estado final

La suite completa queda en:

``` text
37 passed, 1 warning
```

La versión endurecida se desplegó con
`Plan: 0 to add, 1 to change, 0 to destroy` y
`Apply complete! Resources: 0 added, 1 changed, 0 destroyed`.

Bedrock se activó temporalmente para las pruebas E2E con Nova Micro.
Después se restauró y verificó directamente en AWS:

``` text
AI_PROVIDER           mock
REFRIGERATION_SOURCE  mock
TACHOGRAPH_SOURCE     mock
```

El entorno `dev` queda por tanto en modo seguro, sin invocaciones
accidentales a Bedrock.
