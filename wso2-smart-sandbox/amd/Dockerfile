FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Dependencias base (+ Python)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    zip \
    jq \
    python3 \
    python3-yaml \
    ca-certificates \
    gnupg \
    lsb-release \
    netcat \
 && rm -rf /var/lib/apt/lists/*

# Temurin OpenJDK 21
RUN mkdir -p /etc/apt/keyrings \
 && wget -O /etc/apt/keyrings/adoptium.asc https://packages.adoptium.net/artifactory/api/gpg/key/public \
 && echo "deb [signed-by=/etc/apt/keyrings/adoptium.asc] https://packages.adoptium.net/artifactory/deb $(lsb_release -cs) main" \
    > /etc/apt/sources.list.d/adoptium.list \
 && apt-get update \
 && apt-get install -y temurin-21-jdk \
 && rm -rf /var/lib/apt/lists/*

# Magia Multi-Arquitectura para Java
RUN ARCH=$(dpkg --print-architecture) && \
    ln -s /usr/lib/jvm/temurin-21-jdk-$ARCH /usr/lib/jvm/default-jdk

ENV JAVA_HOME=/usr/lib/jvm/default-jdk
ENV PATH=$JAVA_HOME/bin:$PATH

# Instalar WSO2 APIM
WORKDIR /opt

RUN wget https://github.com/wso2/product-apim/releases/download/v4.6.0/wso2am-4.6.0.zip \
 && unzip wso2am-4.6.0.zip \
 && rm wso2am-4.6.0.zip

# --- CORRECCIÓN AQUÍ: Instalador apictl inteligente con Fallbacks ---
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        curl -fsSL "https://github.com/wso2/product-apim-tooling/releases/download/v4.6.0/apictl-4.6.0-linux-arm64.tar.gz" -o apictl.tar.gz || \
        curl -fsSL "https://github.com/wso2/product-apim-tooling/releases/download/v4.4.0/apictl-4.4.0-linux-arm64.tar.gz" -o apictl.tar.gz; \
    else \
        curl -fsSL "https://github.com/wso2/product-apim-tooling/releases/download/v4.6.0/apictl-4.6.0-linux-x64.tar.gz" -o apictl.tar.gz || \
        curl -fsSL "https://github.com/wso2/product-apim-tooling/releases/download/v4.6.0/apictl-4.6.0-linux-amd64.tar.gz" -o apictl.tar.gz || \
        curl -fsSL "https://github.com/wso2/product-apim-tooling/releases/download/v4.4.0/apictl-4.4.0-linux-x64.tar.gz" -o apictl.tar.gz; \
    fi && \
    mkdir -p temp_apictl && \
    tar -xzf apictl.tar.gz -C temp_apictl --strip-components=1 && \
    cp temp_apictl/apictl /usr/local/bin/ && \
    chmod +x /usr/local/bin/apictl && \
    rm -rf temp_apictl apictl.tar.gz

RUN mkdir -p /opt/src/openapi

# -----------------------------------------------------------------
# SCRIPT DE PYTHON PARA GENERAR EL MCP
# -----------------------------------------------------------------
RUN cat <<'EOF' > /opt/mcp_generator.py
import yaml, json, sys, os, re, shutil

oas_file = sys.argv[1]
api_name = sys.argv[2]
api_version = sys.argv[3]
api_id = sys.argv[4]
api_context = sys.argv[5]

with open(oas_file, 'r') as f:
    spec = yaml.safe_load(f)

operations = []
for path, methods in spec.get('paths', {}).items():
    for method, details in methods.items():
        if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']: continue
        
        op_id = details.get('operationId', f"{method}_{re.sub(r'[^a-zA-Z0-9]', '', path)}")
        desc = details.get('summary', details.get('description', f"Executa {method} en {path}"))
        
        props, req = {}, []
        for p in details.get('parameters', []):
            name = p.get('name')
            props[name] = {"description": p.get('description', name)}
            if p.get('required'): req.append(name)
            
        schema = {"type": "object", "properties": props}
        if req: schema["required"] = req
        
        operations.append({
            "id": "",
            "target": op_id,
            "feature": "TOOL",
            "authType": "Application & Application User",
            "throttlingPolicy": "Unlimited",
            "scopes": [],
            "schemaDefinition": json.dumps(schema, indent=2),
            "description": desc,
            "operationPolicies": {"request": [], "response": [], "fault": []},
            "apiOperationMapping": {
                "apiId": api_id,
                "apiName": api_name,
                "apiVersion": api_version,
                "apiContext": api_context,
                "backendOperation": {"target": path, "verb": method.upper()}
            }
        })

mcp_data = {
    "type": "mcp_server",
    "version": "v4.6.0",
    "data": {
        "name": f"MCP_{api_name}",
        "displayName": f"MCP {api_name}",
        "context": f"/mcp{api_name.lower().replace(' ', '')}",
        "version": api_version,
        "provider": "admin",
        "lifeCycleStatus": "PUBLISHED",
        "audiences": ["all"],
        "transport": ["http", "https"],
        "securityScheme": ["oauth_basic_auth_api_key_mandatory", "oauth2"],
        "visibility": "PUBLIC",
        "policies": ["Unlimited"], 
        "subtypeConfiguration": {"subtype": "EXISTING_API"},
        "operations": operations
    }
}

os.makedirs('mcp_build/Definitions', exist_ok=True)
with open('mcp_build/mcp_server.yaml', 'w') as f:
    yaml.dump(mcp_data, f, sort_keys=False)
with open('mcp_build/mcp_server_meta.yaml', 'w') as f:
    yaml.dump({"name": f"MCP_{api_name}", "version": api_version}, f)
shutil.copy(oas_file, 'mcp_build/Definitions/swagger.yaml')
EOF

# -----------------------------------------------------------------
# SCRIPT DE PYTHON PARA GENERAR AI APIs CON GUARDRAILS
# -----------------------------------------------------------------
RUN cat <<'EOF' > /opt/ai_api_generator.py
import yaml, os, sys

llm_name = sys.argv[1]
llm_id = sys.argv[2]
llm_url = sys.argv[3]

project_dir = f"AI_{llm_name}"
os.makedirs(f"{project_dir}/Definitions", exist_ok=True)

# Generamos la API inyectando el SubType (AIAPI) y las Políticas de Guardrails
api_data = {
    "type": "api",
    "version": "v4.6.0",
    "data": {
        "name": f"AI_{llm_name}",
        "context": f"/ai/{llm_id}",
        "version": "1.0.0",
        "provider": "admin",
        "type": "HTTP",
        "subtypeConfiguration": {
            "subtype": "AIAPI",
            "llmProviderId": llm_id,
            "llmProviderName": llm_name
        },
        "endpointConfig": {
            "endpoint_type": "http",
            "production_endpoints": {"url": llm_url},
            "sandbox_endpoints": {"url": llm_url}
        },
        "policies": ["Unlimited"],
        "operations": [
            {
                "target": "/chat/completions",
                "verb": "POST",
                "authType": "Application & Application User",
                "throttlingPolicy": "Unlimited",
                "operationPolicies": {
                    "request": [
                        {
                            "policyName": "cc-word-count-guardrail",
                            "policyVersion": "v1",
                            "parameters": {"maxWordCount": "200"}
                        },
                        {
                            "policyName": "cc-semantic-prompt-guardrail",
                            "policyVersion": "v1",
                            "parameters": {
                                "deniedTopics": "politics, religion, violence, self-harm, hate speech",
                                "action": "BLOCK"
                            }
                        }
                    ],
                    "response": [],
                    "fault": []
                }
            }
        ]
    }
}

with open(f"{project_dir}/api.yaml", 'w') as f:
    yaml.dump(api_data, f, sort_keys=False)

deployments = [{"name": "Default", "vhost": "localhost", "displayOnDevportal": True}]
with open(f"{project_dir}/deployment_environments.yaml", 'w') as f:
    yaml.dump(deployments, f, sort_keys=False)

swagger_data = {
    "openapi": "3.0.1",
    "info": {"title": f"AI_{llm_name}", "version": "1.0.0"},
    "paths": {"/chat/completions": {"post": {"responses": {"200": {"description": "OK"}}}}}
}
with open(f"{project_dir}/Definitions/swagger.yaml", 'w') as f:
    yaml.dump(swagger_data, f, sort_keys=False)
EOF

# -----------------------------------------------------------------
# SCRIPT BASH PRINCIPAL
# -----------------------------------------------------------------
RUN cat <<'EOF' > /opt/start.sh
#!/bin/bash
echo "Iniciando WSO2 API Manager en background..."
sh /opt/wso2am-4.6.0/bin/api-manager.sh start

echo "Esperando a que el servidor levante en el puerto 9443..."
while ! nc -z localhost 9443; do sleep 5; done

echo "Puerto 9443 disponible. Esperando 45 segundos para inicialización interna..."
sleep 45

echo "--- Generando Token REST API Nativo ---"
B64_CRED=$(echo -n "admin:admin" | base64)
DCR_RESPONSE=$(curl -k -s -X POST https://localhost:9443/client-registration/v0.17/register \
  -H "Authorization: Basic $B64_CRED" \
  -H "Content-Type: application/json" \
  -d '{"callbackUrl":"www.google.lk","clientName":"rest_api_client","owner":"admin","grantType":"password refresh_token","saasApp":true}')
CLIENT_ID=$(echo $DCR_RESPONSE | jq -r .clientId)
CLIENT_SECRET=$(echo $DCR_RESPONSE | jq -r .clientSecret)
B64_APP=$(echo -n "$CLIENT_ID:$CLIENT_SECRET" | base64)

TOKEN_RESPONSE=$(curl -k -s -X POST https://localhost:9443/oauth2/token \
  -H "Authorization: Basic $B64_APP" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=admin&password=admin&scope=apim:api_create apim:api_view apim:api_publish apim:app_manage apim:sub_manage apim:subscribe apim:mcp_server_view apim:mcp_server_create apim:mcp_server_manage apim:mcp_server_publish")
TOKEN=$(echo $TOKEN_RESPONSE | jq -r .access_token)

apictl add env dev --apim https://localhost:9443
apictl login dev -u admin -p admin -k

echo "--- 1. Creando Consumidor (AutoTestApp) ---"
APP_ID=$(curl -k -s -X GET "https://localhost:9443/api/am/devportal/v3/applications?query=name:DefaultApplication" -H "Authorization: Bearer $TOKEN" | jq -r '.list[]? | select(.name == "DefaultApplication") | .applicationId' | head -n 1)

if [ "$APP_ID" == "null" ] || [ -z "$APP_ID" ]; then
    echo ">> DefaultApplication no encontrada. Creandola..."
    APP_RESPONSE=$(curl -k -s -X POST "https://localhost:9443/api/am/devportal/v3/applications" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"DefaultApplication","throttlingPolicy":"Unlimited","description":"App por defecto para pruebas"}')
    APP_ID=$(echo $APP_RESPONSE | jq -r '.applicationId')
    sleep 2
fi

echo "--- 2. Procesando OAS -> MOCK -> MCP ---"
for oas_file in /opt/src/openapi/*.yaml /opt/src/openapi/*.json; do
    if [ -f "$oas_file" ]; then
        filename=$(basename -- "$oas_file")
        project_name="${filename%.*}"
        
        echo ">> Construyendo API base: $filename"
        apictl init "$project_name" --oas "$oas_file"
        apictl import api -f "$project_name" -e dev -k --update
        
        api_name=$(grep "^  name:" "$project_name/api.yaml" | head -1 | awk '{print $2}' | tr -d '\r"')
        api_version=$(grep "^  version:" "$project_name/api.yaml" | head -1 | awk '{print $2}' | tr -d '\r"')
        
        API_ID="null"
        RETRIES=0
        while [ "$API_ID" == "null" ] && [ $RETRIES -lt 15 ]; do
            sleep 2
            API_JSON=$(curl -k -s -X GET "https://localhost:9443/api/am/publisher/v4/apis?query=name:$api_name" -H "Authorization: Bearer $TOKEN")
            API_ID=$(echo "$API_JSON" | jq -r '.list[0].id // "null"')
            RETRIES=$((RETRIES+1))
        done
        
        API_CONTEXT=$(echo "$API_JSON" | jq -r '.list[0].context')
        
        if [ "$API_ID" != "null" ] && [ ! -z "$API_ID" ]; then
            echo ">> Configurando Mock (INLINE) y Políticas para la API..."
            curl -k -s -X POST "https://localhost:9443/api/am/publisher/v4/apis/$API_ID/generate-mock-scripts" -H "Authorization: Bearer $TOKEN" > /dev/null
            API_FULL=$(curl -k -s -X GET "https://localhost:9443/api/am/publisher/v4/apis/$API_ID" -H "Authorization: Bearer $TOKEN")
            UPDATED_API=$(echo "$API_FULL" | jq '.endpointImplementationType = "INLINE" | .policies = ["Unlimited"] | del(.authorizationHeader, .securityScheme, .corsConfiguration)')
            curl -k -s -X PUT "https://localhost:9443/api/am/publisher/v4/apis/$API_ID" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$UPDATED_API" > /dev/null
            
            apictl create api-revision -a "$api_name" -v "$api_version" -e dev -k > /dev/null 2>&1 || true
            apictl deploy api-revision -a "$api_name" -v "$api_version" --rev 1 -g Default -e dev -k > /dev/null 2>&1 || true
            curl -k -s -X POST "https://localhost:9443/api/am/publisher/v4/apis/change-lifecycle?apiId=$API_ID&action=Publish" -H "Authorization: Bearer $TOKEN" > /dev/null

            echo ">> Dando tiempo al DevPortal para indexar la API..."
            sleep 4
            curl -k -s -X POST "https://localhost:9443/api/am/devportal/v3/subscriptions" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "{\"applicationId\":\"$APP_ID\",\"apiId\":\"$API_ID\",\"throttlingPolicy\":\"Unlimited\"}" > /dev/null
            
            echo ">> Generando e Importando MCP Server..."
            cd /opt
            rm -rf mcp_build
            python3 mcp_generator.py "$oas_file" "$api_name" "$api_version" "$API_ID" "$API_CONTEXT"
            apictl import mcp-server -f mcp_build -e dev -k --update
            
            MCP_ID="null"
            MCP_RETRIES=0
            while [ "$MCP_ID" == "null" ] && [ $MCP_RETRIES -lt 15 ]; do
                sleep 2
                MCP_JSON=$(curl -k -s -X GET "https://localhost:9443/api/am/publisher/v4/mcp-servers?query=name:MCP_$api_name" -H "Authorization: Bearer $TOKEN")
                MCP_ID=$(echo "$MCP_JSON" | jq -r '.list[0].id // "null"')
                MCP_RETRIES=$((MCP_RETRIES+1))
            done

            if [ "$MCP_ID" != "null" ] && [ "$MCP_ID" != "" ]; then
                REV_RESP=$(curl -k -s -X POST "https://localhost:9443/api/am/publisher/v4/mcp-servers/$MCP_ID/revisions" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"description":"AutoDeploy"}')
                REV_ID=$(echo "$REV_RESP" | jq -r '.id // empty')
                if [ ! -z "$REV_ID" ]; then
                    curl -k -s -X POST "https://localhost:9443/api/am/publisher/v4/mcp-servers/$MCP_ID/deploy-revision?revisionId=$REV_ID" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '[{"name":"Default","vhost":"localhost","displayOnDevportal":true}]' > /dev/null
                fi
                sleep 4
                curl -k -s -X POST "https://localhost:9443/api/am/devportal/v3/subscriptions" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "{\"applicationId\":\"$APP_ID\",\"apiId\":\"$MCP_ID\",\"throttlingPolicy\":\"Unlimited\"}" > /dev/null
            fi
        fi
        rm -rf "$project_name" /opt/mcp_build
    fi
done

echo "--- 3. Generando Claves de Produccion y Sandbox ---"
if [ "$APP_ID" != "null" ] && [ ! -z "$APP_ID" ]; then
    PROD_RESPONSE=$(curl -k -s -X POST "https://localhost:9443/api/am/devportal/v3/applications/$APP_ID/generate-keys" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"keyType":"PRODUCTION","grantTypesToBeSupported":["client_credentials","password"],"validityTime":"360000"}')
    PROD_TOKEN=$(echo $PROD_RESPONSE | jq -r '.token.accessToken')

    SANDBOX_RESPONSE=$(curl -k -s -X POST "https://localhost:9443/api/am/devportal/v3/applications/$APP_ID/generate-keys" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"keyType":"SANDBOX","grantTypesToBeSupported":["client_credentials","password"],"validityTime":"360000"}')
    SANDBOX_TOKEN=$(echo $SANDBOX_RESPONSE | jq -r '.token.accessToken')
    
    >&2 echo ""
    >&2 echo "=================================================================="
    >&2 echo " 🎉 TODO LISTO: API + MOCK + PORTAL + MCP + AI APIs GATEWAY 🎉"
    >&2 echo " "
    >&2 echo " Usa estos tokens en Postman o en tu LLM:"
    >&2 echo " 🔴 Token PRODUCCION : $PROD_TOKEN"
    >&2 echo " 🔵 Token SANDBOX    : $SANDBOX_TOKEN"
    >&2 echo "=================================================================="
    >&2 echo ""
fi

tail -f /opt/wso2am-4.6.0/repository/logs/wso2carbon.log
EOF

RUN chmod +x /opt/start.sh

EXPOSE 9443 9763 8243 8280

CMD ["/opt/start.sh"]