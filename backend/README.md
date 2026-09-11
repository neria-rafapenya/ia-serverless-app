# Backend --- ia-serverless-app

Este directorio contiene el backend de `ia-serverless-app`.

El backend se construye como una API Python con **FastAPI**, ejecutada
de forma serverless en **AWS Lambda**. **Mangum** actúa como adaptador
entre Lambda/API Gateway y la aplicación ASGI de FastAPI.

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
   v
GET /health
```

Actualmente esta arquitectura está desplegada y `GET /health` ha sido
probado correctamente.

## Versiones actuales

``` text
Python   3.12
FastAPI  0.141.1
Mangum   0.22.0
```

AWS Lambda utiliza el runtime `python3.12`.

## Estructura

``` text
backend/
├── app.py
├── lambda_function.py
├── requirements.txt
└── README.md
```

### app.py

Contiene la aplicación FastAPI y sus rutas. Actualmente incluye
`GET /health`.

La respuesta mantiene el contrato existente:

``` json
{
  "message": "ia-serverless-app funcionando",
  "environment": "dev"
}
```

El entorno no está hardcodeado. Se obtiene con:

``` python
os.getenv("ENVIRONMENT", "unknown")
```

Terraform configura `ENVIRONMENT` utilizando `var.environment`.

### lambda_function.py

Es el punto de entrada de AWS Lambda y conecta Lambda con FastAPI
mediante Mangum:

``` python
from mangum import Mangum
from app import app

lambda_handler = Mangum(app)
```

La lógica HTTP permanece en FastAPI y `lambda_function.py` actúa como
adaptador.

### requirements.txt

Dependencias directas:

``` text
fastapi==0.141.1
mangum==0.22.0
```

Las dependencias transitivas, como Pydantic o Starlette, son resueltas
automáticamente por `pip`.

## Entorno virtual

El entorno virtual se crea desde la **raíz del proyecto**:

``` bash
python3.12 -m venv .venv
source .venv/bin/activate
python --version
pip install -r backend/requirements.txt
```

Debe utilizar Python 3.12. El directorio `.venv/` es local y no se
versiona en Git.

## Build para AWS Lambda

El proyecto dispone de `scripts/build_lambda.sh`. Se ejecuta desde la
**raíz del proyecto**:

``` bash
./scripts/build_lambda.sh
```

El script limpia el build anterior, crea `build/lambda/`, instala las
dependencias para **Python 3.12 / Linux x86_64** y copia `app.py` y
`lambda_function.py`.

El resultado es similar a:

``` text
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

`build/` es generado y no se versiona en Git. Terraform comprime este
directorio para crear el ZIP desplegado en Lambda.

## ¿Cuándo ejecutar build_lambda.sh?

Debe volver a ejecutarse antes de `terraform plan` cuando cambie:

``` text
backend/app.py
backend/lambda_function.py
backend/requirements.txt
```

Flujo:

``` text
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

## Onboarding

Después de clonar el repositorio:

``` bash
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

Antes de `terraform apply` se debe revisar qué recursos se crean,
modifican o destruyen y su posible impacto económico.

La autenticación y configuración AWS/Terraform se documentan en la
documentación de infraestructura.

## Flujo de despliegue

``` text
Código FastAPI
      |
      v
backend/
      |
      v
scripts/build_lambda.sh
      |
      v
build/lambda/
      |
      v
Terraform archive_file
      |
      v
lambda.zip
      |
      v
AWS Lambda
      |
      v
API Gateway
```

El despliegue actualiza la Lambda sin mantener servidores encendidos
permanentemente.

## Estado del Capítulo 2

Hasta este punto se ha completado:

-   creación de la aplicación FastAPI;
-   mantenimiento del contrato existente de `/health`;
-   integración FastAPI ↔ Lambda mediante Mangum;
-   alineación del entorno local con Python 3.12;
-   declaración de dependencias en `requirements.txt`;
-   build reproducible para Linux x86_64;
-   empaquetado del backend y sus dependencias;
-   despliegue mediante Terraform;
-   prueba real satisfactoria de `GET /health`.

El backend seguirá evolucionando en los siguientes pasos del proyecto.
