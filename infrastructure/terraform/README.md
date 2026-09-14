# Infraestructura Terraform

Este directorio contiene la infraestructura AWS del proyecto `ia-serverless-app`.

La infraestructura se gestiona mediante Terraform para que pueda recrearse de forma reproducible en otra cuenta o entorno AWS, evitando dependencias manuales y valores hardcodeados siempre que sea posible.

## Archivos

- **`providers.tf`** define los proveedores utilizados por Terraform. Se utilizan AWS y el provider `archive` para empaquetar el código de la Lambda.
- **`variables.tf`** contiene parámetros configurables como la región AWS, el entorno, el nombre del proyecto, el proveedor de IA (`ai_provider`), el modelo Bedrock (`bedrock_model_id`) y el email utilizado para las alertas de presupuesto.
- **`main.tf`** se reserva para recursos generales de infraestructura que se irán añadiendo a medida que evolucione el proyecto.
- **`outputs.tf`** expone datos útiles después del despliegue. Actualmente muestra la URL pública de API Gateway.
- **`budget.tf`** crea un presupuesto mensual de AWS con alertas para controlar el gasto de la cuenta.
- **`iam.tf`** define el rol IAM de la Lambda, sus permisos básicos de CloudWatch y la policy específica de Bedrock con enfoque least privilege.
- **`lambda.tf`** empaqueta el código Python del backend y crea la función AWS Lambda.
- **`cloudwatch.tf`** gestiona el grupo de logs de la Lambda en CloudWatch y configura una retención de 7 días.
- **`api_gateway.tf`** contiene la HTTP API, la integración API Gateway → Lambda, las rutas `GET /health` y `POST /api/chat`, el permiso de invocación y el stage `$default`.
- **`terraform.tfvars`** contiene valores concretos de variables para el entorno local. Este archivo no se versiona.
- **`.terraform.lock.hcl`** fija las versiones de los providers utilizados por Terraform.

## Infraestructura desplegada actualmente

```text
Internet
   |
   v
API Gateway HTTP API
   |
   +--> GET /health
   |
   +--> POST /api/chat
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
   +--> health
   |
   +--> chat_service
           |
           v
       ai_service
           |
           +--> mock      <- activo actualmente
           |
           +--> bedrock   <- preparado, no activo
                    |
                    v
              Nova Micro
              vía Converse

CloudWatch Logs
```

La URL de API Gateway puede consultarse con:

```bash
terraform output api_url
```

La ruta `GET /health` devuelve:

```json
{
  "message": "ia-serverless-app funcionando",
  "environment": "dev"
}
```

## AWS Lambda

Función:

```text
ia-serverless-app-dev-api
```

Configuración actual:

```text
Runtime: Python 3.12
Memoria: 128 MB
Timeout: 10 segundos
ENVIRONMENT: dev
AI_PROVIDER: mock
BEDROCK_MODEL_ID: eu.amazon.nova-micro-v1:0
```

`AI_PROVIDER` se configura desde Terraform mediante `var.ai_provider`.

El valor por defecto continúa siendo:

```text
mock
```

Esto evita que la aplicación invoque Bedrock mientras no se active explícitamente.

El punto de entrada Lambda está en `backend/lambda_function.py`, que utiliza Mangum para adaptar la aplicación FastAPI a AWS Lambda.

Terraform empaqueta el contenido preparado en `build/lambda/` y genera el ZIP de despliegue. El ZIP no se versiona en Git.

## Proveedor de IA configurable

Terraform expone la variable:

```hcl
variable "ai_provider" {
  description = "Proveedor de IA utilizado por el backend"
  type        = string
  default     = "mock"
}
```

La Lambda recibe esta configuración como variable de entorno:

```hcl
environment {
  variables = {
    ENVIRONMENT      = var.environment
    AI_PROVIDER      = var.ai_provider
    BEDROCK_MODEL_ID = var.bedrock_model_id
  }
}
```

El backend obtiene después el valor mediante `AI_PROVIDER`.

Actualmente:

```text
ai_provider = "mock"
```

por lo que `services/ai_service.py` sigue utilizando la implementación simulada en el entorno desplegado.

La rama `bedrock` ya está implementada en el backend, pero todavía no está activada como proveedor efectivo.


### Modelo Bedrock configurable

Terraform expone también:

```hcl
variable "bedrock_model_id" {
  description = "Identificador del modelo o perfil de inferencia utilizado por Amazon Bedrock"
  type        = string
  default     = "eu.amazon.nova-micro-v1:0"
}
```

La Lambda recibe este valor como `BEDROCK_MODEL_ID`. El backend ya no contiene un fallback hardcodeado del modelo; `bedrock_client.py` exige la variable con:

```python
os.environ["BEDROCK_MODEL_ID"]
```

Esto hace explícita la configuración por entorno y mejora la portabilidad.

## Integración preparada con Amazon Bedrock

La infraestructura ya contiene los permisos necesarios para permitir que la Lambda invoque Amazon Bedrock cuando se active `AI_PROVIDER=bedrock`.

El primer modelo preparado es:

```text
Amazon Nova Micro
eu.amazon.nova-micro-v1:0
```

La aplicación utiliza la API `Converse`.

Actualmente no existe capacidad provisionada ni infraestructura Bedrock persistente asociada al proyecto.

La policy IAM por sí sola no genera consumo de Bedrock.

Mientras:

```text
AI_PROVIDER = mock
```

la aplicación no realiza llamadas reales al modelo.

## IAM

La Lambda utiliza el rol:

```text
ia-serverless-app-dev-lambda-role
```

Este rol conserva `AWSLambdaBasicExecutionRole`, que permite escribir logs en CloudWatch.

La estrategia sigue siendo **Least Privilege**.

### Identidad de cuenta dinámica

Para evitar hardcodear el account ID, Terraform obtiene dinámicamente la cuenta actual:

```hcl
data "aws_caller_identity" "current" {}
```

Esto permite construir ARNs dependientes de la cuenta sin acoplar la infraestructura a una cuenta AWS concreta.

### Policy Bedrock

Se ha añadido una policy inline:

```text
aws_iam_role_policy.lambda_bedrock
```

con el permiso:

```text
bedrock:InvokeModel
```

No se utiliza:

```text
bedrock:*
```

La policy permite invocar el perfil de inferencia europeo:

```text
eu.amazon.nova-micro-v1:0
```

y los foundation models asociados en:

```text
eu-central-1
eu-north-1
eu-west-1
eu-west-3
```

El ARN del perfil se construye dinámicamente utilizando:

```text
var.aws_region
data.aws_caller_identity.current.account_id
```

por lo que el account ID no queda hardcodeado en el código Terraform.

## CloudWatch

Grupo de logs:

```text
/aws/lambda/ia-serverless-app-dev-api
```

Retención:

```text
retention_in_days = 7
```

La retención limitada evita mantener logs indefinidamente y forma parte de la estrategia de control de costes.

## API Gateway

Se ha creado una **API Gateway HTTP API** integrada mediante `AWS_PROXY` con la Lambda.

Rutas:

```text
GET  /health
POST /api/chat
```

Stage:

```text
$default
```

con:

```text
auto_deploy = true
```

La ruta `POST /api/chat` ha sido validada de extremo a extremo.

Con `AI_PROVIDER=mock`, una petición como:

```json
{
  "message": "Analiza este documento"
}
```

devuelve:

```json
{
  "response": "[IA simulada][chat] Procesando: Analiza este documento",
  "environment": "dev"
}
```

## AWS Budgets

Se ha configurado un presupuesto mensual de seguridad con alertas al:

```text
50 %
80 %
100 %
100 % forecasted
```

El Budget es un sistema de alerta.

**No es un límite duro de gasto y no detiene automáticamente los servicios AWS.**

Además, el presupuesto actual puede estar influido por costes históricos de recursos anteriores, por lo que debe complementarse con revisión de Cost Explorer y de los planes Terraform.

## Estrategia de costes

Una prioridad permanente del proyecto es evitar infraestructura que genere costes simplemente por estar encendida.

Actualmente usamos principalmente:

```text
API Gateway
Lambda
CloudWatch
IAM
AWS Budgets
```

Bedrock está preparado a nivel de código e IAM, pero no se está invocando todavía porque:

```text
AI_PROVIDER = mock
```

No se ha configurado:

```text
Provisioned Throughput de Bedrock
capacidad reservada de Bedrock
ECS/Fargate permanente
Application Load Balancer
NAT Gateway
RDS
OpenSearch
```

La policy IAM de Bedrock no genera coste por sí sola.

El consumo de Bedrock comenzará únicamente cuando se realicen invocaciones reales al modelo.

Antes de activar Bedrock se están añadiendo controles explícitos:

```text
entrada máxima: 4000 caracteres
salida máxima: 300 tokens
AI_PROVIDER=mock por defecto
IAM mínimo
tests sin llamadas AWS reales
```

El límite de 4000 caracteres ya está cubierto por tests, reconstruido, desplegado y validado mediante API Gateway. Un mensaje vacío devuelve HTTP `422` antes de llegar al proveedor de IA.

## Portabilidad

La infraestructura está diseñada para poder recrearse en otra cuenta AWS.

Evitamos hardcodear:

```text
AWS Account ID
usuario IAM
perfil AWS local
```

Cuando un ARN necesita el account ID, se obtiene dinámicamente mediante:

```hcl
data "aws_caller_identity" "current" {}
```

En desarrollo utilizamos:

```bash
export AWS_PROFILE=ia-serverless-dev
```

pero el perfil no está hardcodeado dentro del provider Terraform.

La región se controla mediante:

```text
var.aws_region
```

y el resto de nombres principales se derivan de:

```text
var.project_name
var.environment
```

## Flujo habitual de trabajo

Antes de desplegar cambios del backend:

```bash
cd backend
pytest -v
cd ..

./scripts/build_lambda.sh

cd infrastructure/terraform
terraform fmt
terraform validate
terraform plan
```

Revisamos siempre:

```text
recursos que se crean
recursos que se modifican
recursos que se destruyen
posible impacto económico
```

Solo después:

```bash
terraform apply
```

## Último cambio validado

Tras externalizar el modelo Bedrock a Terraform, el plan produjo:

```text
Plan: 0 to add, 1 to change, 0 to destroy.
```

El único cambio fue una actualización **in-place** de:

```text
~ aws_lambda_function.api
```

Terraform detectó:

```text
+ BEDROCK_MODEL_ID = eu.amazon.nova-micro-v1:0
~ source_code_hash
```

El `source_code_hash` cambió porque se reconstruyó el paquete después de eliminar el fallback hardcodeado del modelo en Python.

El apply terminó con:

```text
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

No se creó ni destruyó ningún recurso.

## Validación posterior al despliegue

Después del apply se realizó:

```bash
curl -X POST \
  https://h9lsg64yy3.execute-api.eu-west-1.amazonaws.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Analiza este documento"}'
```

Respuesta:

```json
{
  "response": "[IA simulada][chat] Procesando: Analiza este documento",
  "environment": "dev"
}
```

Esto confirma que el recorrido sigue siendo:

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
chat_service
   |
   v
ai_service
   |
   v
AI_PROVIDER=mock
```

Aunque la Lambda ya dispone de código y permisos Bedrock, no se activa el modelo mientras `AI_PROVIDER` permanezca en `mock`.


También se validó la barrera de entrada desplegada:

```text
mensaje válido -> 200
mensaje vacío  -> 422
```

Después de añadir `BEDROCK_MODEL_ID` a la Lambda, se repitió la petición con `"Analiza este documento"` y la respuesta continuó siendo la simulada, confirmando que el proveedor efectivo sigue siendo `mock`.


## Primera invocación real controlada a Bedrock

La integración se ha validado con una primera llamada real a Amazon Bedrock ejecutada desde local, sin cambiar la configuración efectiva de la Lambda pública.

Se utilizó:

```text
AWS_PROFILE=ia-serverless-dev
AWS_DEFAULT_REGION=eu-west-1
BEDROCK_MODEL_ID=eu.amazon.nova-micro-v1:0
```

La llamada se realizó mediante `backend/clients/bedrock_client.py`, usando `boto3` y la API `Converse`.

Respuesta obtenida:

```text
Bedrock funciona.
```

Esto confirma que la configuración de credenciales, región, perfil de inferencia y permisos necesarios para la invocación real son funcionales desde el entorno de desarrollo.

La Lambda desplegada continúa con:

```text
AI_PROVIDER=mock
```

No se ha activado Bedrock en el endpoint público de API Gateway.

La primera llamada real fue intencionadamente local y puntual para evitar que una URL pública sin protección pueda convertirse en una vía de consumo inesperado.

Antes de cambiar la Lambda a:

```text
AI_PROVIDER=bedrock
```

se añadirá una barrera de protección, como autenticación y/o throttling, y se revisará nuevamente el impacto económico.

## Estado actual

```text
Terraform
    |
    +-- AWS Budget
    |
    +-- IAM
    |     |
    |     +-- Lambda execution role
    |     +-- AWSLambdaBasicExecutionRole
    |     +-- aws_caller_identity
    |     +-- Bedrock InvokeModel least privilege
    |
    +-- Lambda Python 3.12
    |       |
    |       +-- ENVIRONMENT
    |       +-- AI_PROVIDER=mock
    |       +-- BEDROCK_MODEL_ID=eu.amazon.nova-micro-v1:0
    |       +-- boto3
    |       +-- Bedrock client preparado
    |
    +-- CloudWatch Logs
    |       |
    |       +-- retención 7 días
    |
    +-- API Gateway HTTP API
            |
            +-- GET /health
            |
            +-- POST /api/chat
                    |
                    v
                  Lambda
                    |
                    v
              FastAPI + Mangum
                    |
                    v
                ai_service
                 /       \
              mock      bedrock
               ↑           |
             activo     preparado
```

## Siguiente paso

La integración básica con Bedrock ya tiene preparados código, cliente, configuración explícita del modelo, permisos IAM, tests y despliegue. `AI_PROVIDER` continúa en `mock`.

El full suite del backend se ha validado con:

```text
12 passed, 1 warning
```

El límite de entrada de 1 a 4000 caracteres ya está desplegado y un mensaje vacío se ha validado con respuesta HTTP `422`.

La primera invocación real a Bedrock ya se ha completado correctamente desde local.

Antes de activar Bedrock en la Lambda pública quedan estos pasos:

```text
1. mantener AI_PROVIDER=mock mientras el endpoint siga sin protección;
2. añadir autenticación y/o throttling;
3. revisar nuevamente el impacto económico;
4. activar Bedrock de forma controlada;
5. comprobar respuesta, logs y coste;
6. volver a AI_PROVIDER=mock cuando se pare temporalmente el desarrollo.
```

El cliente Bedrock ya limita la salida mediante:

```text
maxTokens = 300
```

y el backend está incorporando un máximo de:

```text
4000 caracteres de entrada
```

RAG y otros componentes de IA se incorporarán posteriormente y solo cuando aporten valor al caso de uso y su coste esté justificado.
