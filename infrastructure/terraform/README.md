# Infraestructura Terraform

Este directorio contiene la infraestructura AWS del proyecto
`ia-serverless-app`.

La infraestructura se gestiona mediante Terraform para que pueda
recrearse de forma reproducible en otra cuenta o entorno AWS sin
depender de configuraciones manuales.

## Archivos

-   **providers.tf** define los proveedores utilizados por Terraform. En
    nuestro caso usamos AWS y el provider `archive` para empaquetar el
    código de la Lambda.
-   **variables.tf** contiene parámetros configurables como la región
    AWS, el entorno, el nombre del proyecto, el proveedor de IA
    (`ai_provider`) y el email utilizado para las alertas de presupuesto.
-   **main.tf** se reserva para recursos generales de infraestructura
    que iremos añadiendo a medida que evolucione el proyecto.
-   **outputs.tf** expone datos útiles después de desplegar. Actualmente
    muestra la URL pública de API Gateway.
-   **budget.tf** crea un presupuesto mensual de AWS con alertas para
    controlar el gasto de la cuenta.
-   **iam.tf** define el rol IAM utilizado por la Lambda y sus permisos
    básicos.
-   **lambda.tf** empaqueta el código Python del backend y crea la
    función AWS Lambda.
-   **cloudwatch.tf** gestiona el grupo de logs de la Lambda en
    CloudWatch y configura una retención de 7 días.
-   **api_gateway.tf** contiene la HTTP API, la integración API Gateway
    → Lambda, las rutas `GET /health` y `POST /api/chat`, el permiso de
    invocación y el stage `$default`.
-   **terraform.tfvars** contiene valores concretos de variables para el
    entorno local. Este archivo no se versiona.
-   **.terraform.lock.hcl** fija las versiones de los providers
    utilizados por Terraform.

## Infraestructura desplegada actualmente

``` text
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
           v
     AI_PROVIDER=mock

CloudWatch Logs
```

La URL de API Gateway puede consultarse con:

``` bash
terraform output api_url
```

La ruta `GET /health` devuelve:

``` json
{
  "message": "ia-serverless-app funcionando",
  "environment": "dev"
}
```

## AWS Lambda

Función:

``` text
ia-serverless-app-dev-api
```

Configuración:

``` text
Runtime: Python 3.12
Memoria: 128 MB
Timeout: 10 segundos
ENVIRONMENT: dev
AI_PROVIDER: mock
```

`AI_PROVIDER` se configura desde Terraform mediante `var.ai_provider`.
El valor por defecto es `mock`, lo que evita llamadas reales a servicios
de IA mientras no se active explícitamente otro proveedor.

El punto de entrada Lambda está en `backend/lambda_function.py`, que
utiliza Mangum para adaptar la aplicación FastAPI a AWS Lambda.

Terraform empaqueta el contenido preparado en `build/lambda/` y genera
el ZIP de despliegue, que no se guarda en Git.

## Proveedor de IA configurable

Terraform expone la variable:

``` hcl
variable "ai_provider" {
  description = "Proveedor de IA utilizado por el backend"
  type        = string
  default     = "mock"
}
```

La Lambda recibe esta configuración como variable de entorno:

``` hcl
environment {
  variables = {
    ENVIRONMENT = var.environment
    AI_PROVIDER = var.ai_provider
  }
}
```

El backend obtiene después el valor mediante `AI_PROVIDER`.

Actualmente:

``` text
ai_provider = "mock"
```

por lo que `services/ai_service.py` utiliza una implementación simulada
y no realiza llamadas a Bedrock ni genera consumo de IA.

Más adelante podrá cambiarse a otro proveedor mediante configuración,
sin modificar `chat_service.py` ni las rutas HTTP.

El objetivo es que distintos casos de uso reutilicen la misma capa de
IA indicando su contexto mediante `use_case`, por ejemplo `chat`,
`fridge` o `document`, mientras la lógica de negocio permanece en cada
servicio específico.

## IAM

La Lambda utiliza el rol:

``` text
ia-serverless-app-dev-lambda-role
```

con `AWSLambdaBasicExecutionRole`, que permite escribir logs en
CloudWatch.

La estrategia es mantener **Least Privilege** y añadir únicamente los
permisos necesarios.

## CloudWatch

Grupo de logs:

``` text
/aws/lambda/ia-serverless-app-dev-api
```

Retención:

``` text
retention_in_days = 7
```

## API Gateway

Se ha creado una **API Gateway HTTP API** integrada mediante `AWS_PROXY`
con la Lambda.

Rutas:

``` text
GET  /health
POST /api/chat
```

Stage:

``` text
$default
```

con `auto_deploy = true`.

La ruta `POST /api/chat` ha sido validada de extremo a extremo. Con
`AI_PROVIDER=mock`, una petición como:

``` json
{
  "message": "Analiza este documento"
}
```

devuelve actualmente:

``` json
{
  "response": "[IA simulada][chat] Procesando: Analiza este documento",
  "environment": "dev"
}
```

## AWS Budgets

Se ha configurado un presupuesto mensual de seguridad con alertas al:

``` text
50 %
80 %
100 %
100 % forecasted
```

El Budget es un sistema de alerta. **No es un límite duro de gasto y no
detiene automáticamente los servicios AWS.**

## Estrategia de costes

Una prioridad del proyecto es evitar infraestructura que genere costes
simplemente por estar encendida.

Actualmente usamos principalmente:

``` text
API Gateway
Lambda
CloudWatch
```

Todavía no hemos desplegado:

``` text
ECS/Fargate permanente
Application Load Balancer
NAT Gateway
RDS
OpenSearch
Amazon Bedrock
```

La configuración actual `AI_PROVIDER=mock` permite desarrollar y probar
la integración de IA sin generar llamadas ni coste de modelo.

Antes de incorporar nuevos servicios se revisará su impacto económico.

## Portabilidad

La infraestructura está diseñada para poder recrearse en otra cuenta
AWS.

Evitamos hardcodear:

``` text
AWS Account ID
ARN específicos
usuario IAM
perfil AWS local
```

En desarrollo utilizamos:

``` bash
export AWS_PROFILE=ia-serverless-dev
```

pero el perfil no está hardcodeado en Terraform.

## Flujo habitual de trabajo

Antes de desplegar cambios del backend se ejecutan primero los tests
locales y se reconstruye el paquete Lambda:

``` bash
cd backend
pytest -v
cd ..

./scripts/build_lambda.sh

cd infrastructure/terraform
terraform fmt
terraform validate
terraform plan
```

Revisamos siempre qué recursos se crean, modifican o destruyen y su
posible impacto económico.

Después:

``` bash
terraform apply
```

## Último cambio validado

Al añadir `AI_PROVIDER` a la configuración de la Lambda, Terraform
mostró:

``` text
Plan: 0 to add, 1 to change, 0 to destroy.
```

El único cambio fue una actualización **in-place** de la Lambda:

``` text
+ AI_PROVIDER = "mock"
```

No se creó ningún recurso nuevo ni se destruyó infraestructura.

Después del `apply`, la prueba real mediante API Gateway devolvió:

``` json
{
  "response": "[IA simulada][chat] Procesando: Analiza este documento",
  "environment": "dev"
}
```

Esto valida el recorrido:

``` text
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

## Estado actual

``` text
Terraform
    |
    +-- AWS Budget
    +-- IAM
    +-- Lambda Python 3.12
    |       |
    |       +-- ENVIRONMENT
    |       +-- AI_PROVIDER=mock
    |
    +-- CloudWatch Logs
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
```

El backend serverless con FastAPI y Mangum ya es accesible por HTTP a
través de API Gateway. La configuración del proveedor de IA también está
gestionada explícitamente desde Terraform.

## Siguiente paso

FastAPI, Mangum, `POST /api/chat` y la configuración de `AI_PROVIDER`
ya están implementados.

La siguiente evolución será preparar la integración con un proveedor de
IA real, previsiblemente Amazon Bedrock, manteniendo `mock` como opción
segura y fácilmente seleccionable por configuración.

Antes de activar Bedrock se revisarán específicamente:

``` text
coste por modelo y tokens
permisos IAM mínimos
límites y protección frente a consumo accidental
configuración por entorno
estrategia de pruebas
```

RAG y otros componentes de IA se incorporarán posteriormente y solo
cuando aporten valor al caso de uso.
