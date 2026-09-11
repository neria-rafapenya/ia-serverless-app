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
    AWS, el entorno, el nombre del proyecto y el email utilizado para
    las alertas de presupuesto.
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
    → Lambda, la ruta `GET /health`, el permiso de invocación y el stage
    `$default`.
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
   | GET /health
   v
AWS Lambda
   |
   v
Backend Python
   |
   v
CloudWatch Logs
```

La URL de API Gateway puede consultarse con:

``` bash
terraform output api_url
```

La ruta actual `GET /health` devuelve:

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
```

El código está en `backend/lambda_function.py`. Terraform genera
automáticamente el ZIP de despliegue, que no se guarda en Git.

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

Ruta:

``` text
GET /health
```

Stage:

``` text
$default
```

con `auto_deploy = true`.

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
```

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

Antes de desplegar:

``` bash
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

## Estado actual

``` text
Terraform
    |
    +-- AWS Budget
    +-- IAM
    +-- Lambda Python
    +-- CloudWatch Logs
    +-- API Gateway HTTP API
            |
            +-- GET /health
                    |
                    +-- Lambda
```

El backend serverless ya es accesible por HTTP a través de API Gateway.

## Siguiente paso

La siguiente evolución prevista es sustituir la Lambda Python mínima
por:

``` text
FastAPI + Mangum
```

manteniendo inicialmente AWS Lambda como entorno de ejecución
serverless.

Esto permitirá evolucionar hacia:

``` text
GET  /health
POST /api/chat
```

y posteriormente integrar Amazon Bedrock, RAG y otros componentes de la
arquitectura de IA.
