# Infraestructura Terraform

Este directorio contiene la infraestructura AWS del proyecto
`ia-serverless-app`.

La infraestructura se gestiona mediante Terraform para que pueda
recrearse de forma reproducible en otra cuenta o entorno AWS, evitando
dependencias manuales y valores hardcodeados siempre que sea posible.

## Archivos

-   **`providers.tf`** define los proveedores utilizados por Terraform.
    Se utilizan AWS y el provider `archive` para empaquetar el código de
    la Lambda.
-   **`variables.tf`** contiene parámetros configurables como la región
    AWS, el entorno, el nombre del proyecto, el proveedor de IA
    (`ai_provider`), el modelo Bedrock (`bedrock_model_id`) y el email
    utilizado para las alertas de presupuesto.
-   **`main.tf`** se reserva para recursos generales de infraestructura
    que se irán añadiendo a medida que evolucione el proyecto.
-   **`outputs.tf`** expone datos útiles después del despliegue.
    Actualmente muestra la URL pública de API Gateway.
-   **`budget.tf`** crea un presupuesto mensual de AWS con alertas para
    controlar el gasto de la cuenta.
-   **`iam.tf`** define el rol IAM de la Lambda, sus permisos básicos de
    CloudWatch y la policy específica de Bedrock con enfoque least
    privilege.
-   **`lambda.tf`** empaqueta el código Python del backend y crea la
    función AWS Lambda.
-   **`cloudwatch.tf`** gestiona el grupo de logs de la Lambda en
    CloudWatch y configura una retención de 7 días.
-   **`api_gateway.tf`** contiene la HTTP API, la integración API
    Gateway → Lambda, las rutas `GET /health`, `POST /api/chat`,
    `POST /api/documents/upload-url`, `GET /api/refrigeration/status` y
    `GET /api/tachograph/status`, el permiso de invocación, el stage
    `$default`, el throttling por ruta y el JWT authorizer de Cognito.
-   **`cognito.tf`** crea el Cognito User Pool y el App Client web
    utilizado para autenticar usuarios.
-   **`terraform.tfvars`** contiene valores concretos de variables para
    el entorno local. Este archivo no se versiona.
-   **`.terraform.lock.hcl`** fija las versiones de los providers
    utilizados por Terraform.

## Infraestructura desplegada actualmente

``` text
Internet
   |
   v
API Gateway HTTP API
   |
   +--> GET /health (público)
   |
   +--> POST /api/chat
           |
           +--> JWT authorizer -> Cognito User Pool
           +--> throttling 2 req/s, burst 5
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
           +--> mock      <- valor seguro por defecto
           |
           +--> bedrock   <- preparado y validado; actualmente desactivado
                    |
                    v
              Nova Micro
              vía Converse

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

Configuración actual:

``` text
Runtime: Python 3.12
Memoria: 128 MB
Timeout: 10 segundos
ENVIRONMENT: dev
AI_PROVIDER: mock
BEDROCK_MODEL_ID: eu.amazon.nova-micro-v1:0
```

`AI_PROVIDER` se configura desde Terraform mediante `var.ai_provider`.

El valor por defecto continúa siendo:

``` text
mock
```

Esto evita que la aplicación invoque Bedrock mientras no se active
explícitamente.

El punto de entrada Lambda está en `backend/lambda_function.py`, que
utiliza Mangum para adaptar la aplicación FastAPI a AWS Lambda.

Terraform empaqueta el contenido preparado en `build/lambda/` y genera
el ZIP de despliegue. El ZIP no se versiona en Git.

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
    ENVIRONMENT      = var.environment
    AI_PROVIDER      = var.ai_provider
    BEDROCK_MODEL_ID = var.bedrock_model_id
  }
}
```

El backend obtiene después el valor mediante `AI_PROVIDER`.

El valor por defecto en `variables.tf` sigue siendo `mock` como medida
segura. En el entorno `dev`, `terraform.tfvars` sobrescribe
explícitamente ese valor con:

``` text
ai_provider = "mock"
```

por lo que `services/ai_service.py` utiliza el proveedor mock y no
invoca Amazon Bedrock. Para usar Bedrock es necesario cambiar
explícitamente el valor a `bedrock`.

### Modelo Bedrock configurable

Terraform expone también:

``` hcl
variable "bedrock_model_id" {
  description = "Identificador del modelo o perfil de inferencia utilizado por Amazon Bedrock"
  type        = string
  default     = "eu.amazon.nova-micro-v1:0"
}
```

La Lambda recibe este valor como `BEDROCK_MODEL_ID`. El backend ya no
contiene un fallback hardcodeado del modelo; `bedrock_client.py` exige
la variable con:

``` python
os.environ["BEDROCK_MODEL_ID"]
```

Esto hace explícita la configuración por entorno y mejora la
portabilidad.

## Integración preparada con Amazon Bedrock

La infraestructura ya contiene los permisos necesarios para permitir que
la Lambda invoque Amazon Bedrock cuando se active `AI_PROVIDER=bedrock`.

El primer modelo preparado es:

``` text
Amazon Nova Micro
eu.amazon.nova-micro-v1:0
```

La aplicación utiliza la API `Converse`.

Actualmente no existe capacidad provisionada ni infraestructura Bedrock
persistente asociada al proyecto.

La policy IAM por sí sola no genera consumo de Bedrock. El consumo
comienza únicamente cuando una petición autenticada alcanza una ruta que
requiere IA y se invoca el modelo.

## IAM

La Lambda utiliza el rol:

``` text
ia-serverless-app-dev-lambda-role
```

Este rol conserva `AWSLambdaBasicExecutionRole`, que permite escribir
logs en CloudWatch.

La estrategia sigue siendo **Least Privilege**.

### Identidad de cuenta dinámica

Para evitar hardcodear el account ID, Terraform obtiene dinámicamente la
cuenta actual:

``` hcl
data "aws_caller_identity" "current" {}
```

Esto permite construir ARNs dependientes de la cuenta sin acoplar la
infraestructura a una cuenta AWS concreta.

### Policy Bedrock

Se ha añadido una policy inline:

``` text
aws_iam_role_policy.lambda_bedrock
```

con el permiso:

``` text
bedrock:InvokeModel
```

No se utiliza:

``` text
bedrock:*
```

La policy permite invocar el perfil de inferencia europeo:

``` text
eu.amazon.nova-micro-v1:0
```

y los foundation models asociados en:

``` text
eu-central-1
eu-north-1
eu-west-1
eu-west-3
```

El ARN del perfil se construye dinámicamente utilizando:

``` text
var.aws_region
data.aws_caller_identity.current.account_id
```

por lo que el account ID no queda hardcodeado en el código Terraform.

## CloudWatch

Grupo de logs:

``` text
/aws/lambda/ia-serverless-app-dev-api
```

Retención:

``` text
retention_in_days = 7
```

La retención limitada evita mantener logs indefinidamente y forma parte
de la estrategia de control de costes.

## API Gateway

Se ha creado una **API Gateway HTTP API** integrada mediante `AWS_PROXY`
con la Lambda.

Rutas actuales:

``` text
GET  /health
POST /api/chat
POST /api/documents/upload-url
GET  /api/refrigeration/status
GET  /api/tachograph/status
```

Stage:

``` text
$default
```

con:

``` text
auto_deploy = true
```

La ruta `POST /api/chat` fue validada de extremo a extremo con
autenticación JWT y, durante una prueba controlada anterior, con Bedrock
activo. Actualmente `AI_PROVIDER=mock`. Las rutas de refrigeración y
tacógrafos también están protegidas por JWT y se han validado con
`401 Unauthorized` sin token y `200 OK` con JWT válido.

## AWS Budgets

Se ha configurado un presupuesto mensual de seguridad con alertas al:

``` text
50 %
80 %
100 %
100 % forecasted
```

El Budget es un sistema de alerta.

**No es un límite duro de gasto y no detiene automáticamente los
servicios AWS.**

Además, el presupuesto actual puede estar influido por costes históricos
de recursos anteriores, por lo que debe complementarse con revisión de
Cost Explorer y de los planes Terraform.

## Estrategia de costes

> **Estado actual de IA:** la integración con Amazon Bedrock ya fue
> validada correctamente desde local y desde la API protegida, pero
> `AI_PROVIDER` ha vuelto a `mock` mientras se desarrollan los servicios
> de dominio. Esto evita invocaciones accidentales y mantiene el control
> de costes.

Una prioridad permanente del proyecto es evitar infraestructura que
genere costes simplemente por estar encendida.

Actualmente usamos principalmente:

``` text
API Gateway
Lambda
CloudWatch
IAM
AWS Budgets
```

Bedrock está preparado y validado, pero actualmente el entorno `dev`
vuelve a usar:

``` text
AI_PROVIDER = mock
```

El valor por defecto de Terraform continúa siendo `mock`, de modo que
otros entornos no activan Bedrock salvo que se configure explícitamente.

No se ha configurado:

``` text
Provisioned Throughput de Bedrock
capacidad reservada de Bedrock
ECS/Fargate permanente
Application Load Balancer
NAT Gateway
RDS
OpenSearch
```

La policy IAM de Bedrock no genera coste por sí sola.

El consumo de Bedrock se produce únicamente cuando se realizan
invocaciones reales al modelo. La primera llamada E2E desde la API
protegida ya se ha validado correctamente.

Antes de activar Bedrock se han añadido controles explícitos:

``` text
entrada máxima: 4000 caracteres
salida máxima: 300 tokens
AI_PROVIDER=mock por defecto
IAM mínimo
throttling en POST /api/chat
autenticación JWT con Cognito
tests sin llamadas AWS reales
```

El límite de 4000 caracteres ya está cubierto por tests, reconstruido,
desplegado y validado mediante API Gateway. Un mensaje vacío devuelve
HTTP `422` antes de llegar al proveedor de IA.

## Portabilidad

La infraestructura está diseñada para poder recrearse en otra cuenta
AWS.

Evitamos hardcodear:

``` text
AWS Account ID
usuario IAM
perfil AWS local
```

Cuando un ARN necesita el account ID, se obtiene dinámicamente mediante:

``` hcl
data "aws_caller_identity" "current" {}
```

En desarrollo utilizamos:

``` bash
export AWS_PROFILE=ia-serverless-dev
```

pero el perfil no está hardcodeado dentro del provider Terraform.

La región se controla mediante:

``` text
var.aws_region
```

y el resto de nombres principales se derivan de:

``` text
var.project_name
var.environment
```

## Flujo habitual de trabajo

Antes de desplegar cambios del backend:

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

Revisamos siempre:

``` text
recursos que se crean
recursos que se modifican
recursos que se destruyen
posible impacto económico
```

Solo después:

``` bash
terraform apply
```

## Último cambio validado

El último módulo incorporado es el servicio de tacógrafos.

La creación de la nueva ruta protegida y la actualización del throttling
produjeron:

``` text
Plan: 1 to add, 1 to change, 0 to destroy.
```

Los cambios fueron:

``` text
+ aws_apigatewayv2_route.tachograph_status
~ aws_apigatewayv2_stage.default
```

El apply terminó con:

``` text
Apply complete! Resources: 1 added, 1 changed, 0 destroyed.
```

Después se reconstruyó el paquete Lambda con `scripts/build_lambda.sh`.
Terraform detectó únicamente el cambio de código de la función:

``` text
Plan: 0 to add, 1 to change, 0 to destroy.
```

El recurso actualizado fue:

``` text
~ aws_lambda_function.api
```

y el apply terminó con:

``` text
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

No se destruyó ningún recurso ni se añadió infraestructura siempre
encendida.

## Validación posterior al despliegue

Se validaron primero los controles de acceso:

``` text
GET  /health sin JWT                       -> 200
POST /api/chat sin JWT                     -> 401 Unauthorized
POST /api/chat con JWT                     -> 200
GET  /api/refrigeration/status sin JWT     -> 401 Unauthorized
GET  /api/refrigeration/status con JWT     -> 200
GET  /api/tachograph/status sin JWT        -> 401 Unauthorized
GET  /api/tachograph/status con JWT válido -> 200
```

Después de activar `AI_PROVIDER=bedrock`, se ejecutó una petición
autenticada a:

``` text
POST /api/chat
```

con un mensaje que activa la rama de IA:

``` text
Explica en una frase qué es AWS Lambda
```

La respuesta fue HTTP `200` y el contenido fue generado por Amazon Nova
Micro. El recorrido validado es:

``` text
Cognito JWT
   |
   v
API Gateway JWT authorizer
   |
   +-- throttling en POST /api/chat
   |
   v
Lambda
   |
   v
FastAPI + Mangum
   |
   v
chat_service
   |
   v
ai_service
   |
   v
AI_PROVIDER=bedrock
   |
   v
Amazon Bedrock / Nova Micro
```

La entrada continúa limitada a 4000 caracteres y la salida del modelo a
300 tokens.

## Validaciones reales de Bedrock

La integración se ha validado con una primera llamada real a Amazon
Bedrock ejecutada desde local, sin cambiar la configuración efectiva de
la Lambda pública.

Se utilizó:

``` text
AWS_PROFILE=ia-serverless-dev
AWS_DEFAULT_REGION=eu-west-1
BEDROCK_MODEL_ID=eu.amazon.nova-micro-v1:0
```

La llamada se realizó mediante `backend/clients/bedrock_client.py`,
usando `boto3` y la API `Converse`.

Respuesta obtenida:

``` text
Bedrock funciona.
```

Esto confirma que la configuración de credenciales, región, perfil de
inferencia y permisos necesarios para la invocación real son funcionales
desde el entorno de desarrollo.

Esa primera llamada fue intencionadamente local y puntual.
Posteriormente se añadieron throttling y autenticación JWT con Cognito
y, una vez validados ambos controles, se activó Bedrock en la Lambda del
entorno `dev`. La primera llamada real desde la API protegida también se
validó correctamente con HTTP `200`.

## Servicio de refrigeración

Se ha incorporado un primer servicio de dominio para monitorización de
dispositivos de refrigeración. La lógica está desacoplada de la fuente
de datos para poder sustituir el mock actual por una API, IoT u otra
integración externa sin modificar las reglas de negocio.

### Flujo

``` text
Cliente autenticado
  |
  v
API Gateway
  |
  +--> JWT Cognito
  +--> throttling 2 req/s, burst 5
  |
  v
Lambda / FastAPI
  |
  v
refrigeration_service.py
  |
  v
refrigeration_source.py
  |
  +--> mock JSON (actual)
  +--> API externa (futura)
```

### Endpoint

``` text
GET /api/refrigeration/status
```

La ruta está protegida por el JWT authorizer de Cognito.

Validación E2E realizada:

``` text
GET /api/refrigeration/status sin JWT        -> 401 Unauthorized
GET /api/refrigeration/status con JWT válido -> 200 OK
```

La respuesta validada contiene cuatro dispositivos de prueba:

``` text
FRIDGE-001 -> NORMAL
FRIDGE-002 -> WARNING
FRIDGE-003 -> CRITICAL
FRIDGE-004 -> OFFLINE
```

### Fuente configurable

La integración se encuentra en:

``` text
backend/integrations/refrigeration_source.py
```

La fuente se selecciona mediante:

``` text
REFRIGERATION_SOURCE
```

El valor seguro por defecto es `mock`. Los datos de prueba se cargan
desde:

``` text
backend/mocks/refrigeration_data.json
```

La rama `api` queda preparada para una futura integración real y
actualmente no está implementada.

### Reglas deterministas

La clasificación se ejecuta en:

``` text
backend/services/refrigeration_service.py
```

Estados actuales:

``` text
NORMAL
WARNING
CRITICAL
OFFLINE
```

Los umbrales actuales son valores de demostración:

``` text
warning  = 7.0 °C
critical = 20.0 °C
```

No deben interpretarse como límites regulatorios ni como reglas
definitivas de negocio. En una integración real deberán configurarse
según cliente, producto, dispositivo o normativa aplicable.

La clasificación es determinista y no requiere IA.

### Throttling

API Gateway aplica a `GET /api/refrigeration/status`:

``` text
Rate limit:  2 peticiones/segundo
Burst limit: 5 peticiones
```

El despliegue del throttling actualizó únicamente el stage existente:

``` text
Plan: 0 to add, 1 to change, 0 to destroy.
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

No se creó nueva infraestructura persistente.

### Build de Lambda

`scripts/build_lambda.sh` copia ahora también:

``` text
backend/integrations/
backend/mocks/
```

además de `backend/services/` y `backend/clients/`.

Este ajuste fue necesario para que la Lambda desplegada pudiera importar
la integración de refrigeración y leer el JSON mock.

### Tests

La suite completa del backend queda actualmente en:

``` text
37 passed, 1 warning
```

Se han añadido pruebas para `NORMAL`, `WARNING`, `CRITICAL` y `OFFLINE`,
además de una prueba del endpoint HTTP.

### Coste

El servicio reutiliza la Lambda y API Gateway existentes. No se ha
añadido una Lambda adicional ni infraestructura siempre encendida. La
fuente actual es un mock local empaquetado con la Lambda.

## Servicio de tacógrafos

Se ha incorporado un segundo servicio de dominio para monitorización de
tacógrafos. Mantiene el mismo patrón desacoplado utilizado en
refrigeración:

``` text
fuente externa / mock
        |
        v
tachograph_source.py
        |
        v
tachograph_service.py
        |
        v
reglas deterministas
        |
        v
endpoint protegido
```

### Endpoint

``` text
GET /api/tachograph/status
```

La ruta está protegida por el JWT authorizer de Cognito y reutiliza la
misma Lambda y la misma HTTP API existentes.

Validación E2E realizada:

``` text
GET /api/tachograph/status sin JWT        -> 401 Unauthorized
GET /api/tachograph/status con JWT válido -> 200 OK
```

La respuesta validada contiene cuatro conductores/vehículos de prueba:

``` text
DRIVER-001 -> NORMAL
DRIVER-002 -> WARNING
DRIVER-003 -> CRITICAL
DRIVER-004 -> OFFLINE
```

### Fuente configurable

La integración se encuentra en:

``` text
backend/integrations/tachograph_source.py
```

La fuente se selecciona mediante:

``` text
TACHOGRAPH_SOURCE
```

El valor seguro por defecto es:

``` text
mock
```

Los datos de prueba se cargan desde:

``` text
backend/mocks/tachograph_data.json
```

La rama `api` está preparada para una futura integración real y
actualmente lanza `NotImplementedError`.

### Reglas deterministas

La clasificación se ejecuta en:

``` text
backend/services/tachograph_service.py
```

Estados actuales:

``` text
NORMAL
WARNING
CRITICAL
OFFLINE
```

Los umbrales actuales son de demostración:

``` text
warning  = 480 minutos
critical = 540 minutos
```

Estos valores no deben interpretarse como una implementación completa de
la normativa de tacógrafos. Son umbrales de demo para validar
arquitectura, flujo y observabilidad. Si más adelante se implementa
cumplimiento normativo real, deberán modelarse reglas adicionales y
verificarse contra fuentes oficiales vigentes.

La clasificación actual es determinista y no requiere Bedrock.

### Throttling

API Gateway aplica a:

``` text
GET /api/tachograph/status
```

los límites:

``` text
Rate limit:  2 peticiones/segundo
Burst limit: 5 peticiones
```

La incorporación de la ruta produjo:

``` text
Plan: 1 to add, 1 to change, 0 to destroy.
Apply complete! Resources: 1 added, 1 changed, 0 destroyed.
```

El recurso creado fue la ruta de API Gateway y el stage `$default` se
actualizó in-place para añadir sus `route_settings`.

### Despliegue de Lambda

Tras reconstruir el paquete:

``` bash
./scripts/build_lambda.sh
```

Terraform detectó únicamente el cambio del ZIP:

``` text
Plan: 0 to add, 1 to change, 0 to destroy.
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

El único recurso actualizado fue:

``` text
aws_lambda_function.api
```

El script de build ya copia carpetas completas:

``` text
backend/services/
backend/clients/
backend/integrations/
backend/mocks/
```

por lo que los nuevos archivos de tacógrafos quedan incluidos sin añadir
reglas específicas al script.

### Tests

Se añadieron cuatro tests unitarios para el servicio y una prueba HTTP
del nuevo endpoint.

La suite completa del backend queda actualmente en:

``` text
37 passed, 1 warning
```

### Coste

El módulo reutiliza API Gateway, Cognito y la Lambda existentes. No se
ha añadido una Lambda adicional ni infraestructura siempre encendida. La
fuente actual es un JSON mock empaquetado con la Lambda, por lo que este
módulo no introduce un coste fijo nuevo de infraestructura.

## Estado actual

``` text
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
                           ↑
                         activo
```

## Estado de la integración Bedrock

La integración básica con Bedrock está preparada y validada: código,
cliente, modelo configurable, permisos IAM, tests y despliegue
funcionan. Actualmente `dev` usa `AI_PROVIDER=mock` para evitar consumo
accidental.

El full suite del backend se ha validado con:

``` text
37 passed, 1 warning
```

El límite de entrada es de 1 a 4000 caracteres y el cliente Bedrock
limita la salida mediante:

``` text
maxTokens = 300
```

La primera invocación real se validó primero desde local y después desde
la API protegida con Cognito y throttling. El entorno `dev` utiliza
actualmente:

``` text
AI_PROVIDER=mock
```

El valor por defecto en Terraform sigue siendo `mock`. Cuando se detenga
temporalmente el desarrollo se debe volver a `mock` para evitar consumo
accidental.

RAG y otros componentes de IA se incorporarán posteriormente y solo
cuando aporten valor al caso de uso y su coste esté justificado.

## Throttling de `POST /api/chat`

API Gateway aplica un límite específico a la ruta de chat mediante
`route_settings` en el stage `$default`:

``` hcl
route_settings {
  route_key = aws_apigatewayv2_route.chat.route_key

  throttling_rate_limit  = 2
  throttling_burst_limit = 5
}
```

Esto limita aproximadamente el tráfico sostenido a 2 peticiones por
segundo, con una ráfaga de hasta 5 peticiones.

`GET /health` queda fuera de este límite específico.

### Despliegue

El cambio se aplicó sin crear ni destruir recursos:

``` text
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

El único recurso actualizado fue:

``` text
aws_apigatewayv2_stage.default
```

### Prueba de integración

Antes de activar Bedrock, con `AI_PROVIDER=mock`, se lanzó una prueba
contra la API con 100 peticiones y concurrencia 25.

Resultado final:

``` text
42 200
58 429
```

La presencia de `429 Too Many Requests` confirma que el throttling está
activo en API Gateway.

Una ejecución anterior produjo:

``` text
66 200
18 429
16 503
```

La segunda ejecución validó el comportamiento esperado de forma limpia
mediante `429`.

### Alcance del control

El throttling reduce el riesgo de abuso y limita la velocidad a la que
las peticiones pueden alcanzar Lambda y Bedrock. Sin embargo:

-   es un mecanismo de limitación de tráfico, no de autenticación;
-   no establece un presupuesto mensual;
-   se complementa con autenticación JWT y límites de entrada/salida
    para reducir el riesgo de consumo no deseado.

Estas pruebas de carga se realizaron antes de activar Bedrock, por lo
que no generaron consumo de modelo. Actualmente `dev` utiliza
`AI_PROVIDER=mock` para evitar consumo accidental.

## Amazon Cognito y JWT authorizer

Se ha añadido `cognito.tf` con dos recursos:

``` text
aws_cognito_user_pool.users
aws_cognito_user_pool_client.web
```

Configuración principal:

``` text
Login: email
Auto-verificación: email
MFA: desactivado
App Client: sin client secret
Auth flow: ALLOW_USER_PASSWORD_AUTH
Refresh token: habilitado
```

No se han añadido SMS, MFA de pago, Cognito Plus ni infraestructura
persistente adicional. Para el POC se mantiene una configuración mínima
orientada a coste bajo.

API Gateway utiliza un authorizer de tipo `JWT`:

``` text
issuer   -> endpoint del Cognito User Pool
audience -> App Client ID de Cognito
identity -> Authorization header
```

Las rutas protegidas incluyen:

``` text
POST /api/chat
POST /api/documents/upload-url
GET  /api/refrigeration/status
GET  /api/tachograph/status
```

La ruta de salud continúa pública:

``` text
GET /health
```

### Despliegue de Cognito

El User Pool y el App Client se desplegaron con:

``` text
Apply complete! Resources: 2 added, 0 changed, 0 destroyed.
```

Después se añadió el JWT authorizer y se modificó la ruta de chat:

``` text
Apply complete! Resources: 1 added, 1 changed, 0 destroyed.
```

No se destruyó ningún recurso. La Lambda y su configuración de IA no
cambiaron durante este módulo.

### Validación E2E

Se creó un usuario de prueba de forma controlada, se estableció una
contraseña permanente y se confirmó el estado:

``` text
UserStatus: CONFIRMED
```

Pruebas realizadas:

``` text
GET  /health sin token        -> 200 OK
POST /api/chat sin token      -> 401 Unauthorized
POST /api/chat con JWT válido -> 200 OK
```

Respuesta autenticada confirmada:

``` json
{
  "response": "Mensaje recibido: Hola",
  "environment": "dev"
}
```

Esto confirma el flujo:

``` text
Usuario
  |
  v
Cognito -> JWT
  |
  v
API Gateway
  |
  +--> valida JWT
  +--> aplica throttling
  |
  v
Lambda -> FastAPI
```

Las primeras pruebas de autenticación se realizaron todavía con
`AI_PROVIDER=mock`, por lo que no invocaron Bedrock. Después se activó
`AI_PROVIDER=bedrock` y se validó una petición autenticada real con HTTP
`200`.

## Estado de protección de la ruta de IA

La ruta de chat dispone ahora de varias barreras complementarias:

``` text
JWT Cognito              -> impide uso anónimo
throttling API Gateway   -> limita velocidad de peticiones
message max_length=4000  -> limita entrada
maxTokens=300            -> limita salida futura del LLM
AI_PROVIDER=mock         -> estado actual seguro en dev; Bedrock queda preparado para activación controlada
```

La activación de Bedrock se validó de forma controlada en una fase
anterior. Actualmente `AI_PROVIDER=mock`, por lo que el backend conserva
la integración preparada sin realizar invocaciones accidentales al
modelo.

------------------------------------------------------------------------

## Integración IA de los servicios de dominio

Se han añadido las rutas protegidas `GET /api/refrigeration/analysis` y
`GET /api/tachograph/analysis`. Reutilizan API Gateway, Cognito, la
integración `AWS_PROXY` y la Lambda existentes; no se ha creado
infraestructura siempre encendida adicional.

Las rutas deterministas `/api/refrigeration/status` y
`/api/tachograph/status` mantienen `2 req/s, burst 5`. Las rutas
`/analysis`, que pueden invocar IA, usan `1 req/s, burst 2`.

Terraform externaliza `refrigeration_source` y `tachograph_source`,
ambas con `default = "mock"`, y Lambda recibe `REFRIGERATION_SOURCE` y
`TACHOGRAPH_SOURCE`. Las futuras credenciales de APIs externas no
deberán almacenarse en `terraform.tfvars`.

Después de endurecer los prompts, el despliegue de código produjo
únicamente:

``` text
Plan: 0 to add, 1 to change, 0 to destroy.
Apply complete! Resources: 0 added, 1 changed, 0 destroyed.
```

Tras las pruebas E2E se restauró:

``` hcl
ai_provider = "mock"
refrigeration_source = "mock"
tachograph_source    = "mock"
```

El último plan mostró exclusivamente `AI_PROVIDER = "bedrock" -> "mock"`
y el apply finalizó con `0 added, 1 changed, 0 destroyed`.

La configuración efectiva se verificó directamente en AWS:

``` text
AI_PROVIDER           mock
REFRIGERATION_SOURCE  mock
TACHOGRAPH_SOURCE     mock
```

### Impacto económico

El módulo reutiliza recursos existentes. No introduce ECS/Fargate,
balanceadores, NAT Gateway, RDS, OpenSearch ni capacidad provisionada de
Bedrock. `/status` es determinista y no necesita Bedrock; `/analysis`
solo puede generar consumo de modelo con `AI_PROVIDER=bedrock`,
actualmente desactivado.
