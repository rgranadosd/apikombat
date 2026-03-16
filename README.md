# 🚀 WSO2 APIM & MCP Zero-Click Automator

A fully automated, containerized solution to spin up a complete WSO2 API Manager 4.6.0 environment from a simple OpenAPI Specification (OAS). 

This project is designed to drastically reduce the time needed to create demonstrations, test environments, and AI-ready API integrations. Just drop your Swagger/OAS file, run a single Docker command, and get a fully published API with mocking, a deployed Model Context Protocol (MCP) server, and ready-to-use OAuth2 tokens.

## ✨ Features (The "Zero-Click" Magic)

By simply running Docker Compose, this automation pipeline performs the following steps without any human intervention:

1. **APIM Initialization:** Spins up a fresh instance of WSO2 API Manager 4.6.0.
2. **OAS to API:** Automatically parses your OpenAPI file and creates a Publisher API.
3. **Auto-Mocking:** Configures an `INLINE` backend mock based on the examples provided in your OAS file (No real backend required!).
4. **MCP Server Generation:** Dynamically runs a Python script to translate your OAS into an LLM-compatible MCP (Model Context Protocol) Server.
5. **Gateway Deployment:** Deploys both the API and the MCP Server to the Default Gateway and publishes them.
6. **Consumer Automation:** Creates a `DefaultApplication` in the Developer Portal.
7. **Auto-Subscription:** Subscribes the application to both the API and the MCP Server with an "Unlimited" business plan.
8. **Token Generation:** Automatically generates Production and Sandbox OAuth2 access tokens and prints them directly to your console.

## 📁 Directory Structure

Ensure your project follows this structure before running:

```text
.
├── docker-compose.yml
├── Dockerfile
└── src/
    └── openapi/
        └── your_openapi_spec.yaml  <-- Drop your OAS 3.0/Swagger file here!
```
*(Note: You can place `.yaml` or `.json` files inside the `src/openapi/` folder).*

## 🚀 Getting Started

### Prerequisites
* Docker
* Docker Compose

### Execution

1. Place your OpenAPI specification file inside the `./src/openapi/` directory.
2. Open your terminal in the root directory of this project.
3. Run the following command:

```bash
docker-compose down -v && docker-compose up --build
```
*(Using `down -v` ensures a clean WSO2 database on every fresh start).*

### 🎯 What to Expect

The build process will download WSO2, setup `apictl`, and start the server. Once the server is up, the automation script will trigger. Keep an eye on your terminal; once the process finishes, you will be greeted with a success banner containing your tokens:

```text
==================================================================
 🎉 TODO LISTO: API + MOCK + PORTAL + MCP SERVER DESPLEGADO 🎉
 
 Usa estos tokens en Postman o en tu LLM:
 🔴 Token PRODUCCION : eyJhbGciOiJSUzI1...
 🔵 Token SANDBOX    : eyJhbGciOiJSUzI1...
==================================================================
```

## 🌐 Accessing the Portals

You can access the WSO2 Web Interfaces using the default credentials (`admin` / `admin`):

* **Publisher Portal:** [https://localhost:9443/publisher](https://localhost:9443/publisher)
* **Developer Portal:** [https://localhost:9443/devportal](https://localhost:9443/devportal)
* **Carbon Management Console:** [https://localhost:9443/carbon](https://localhost:9443/carbon)

## 🛠️ Testing Your Setup

* **Standard API:** Open Postman, paste your `PRODUCCION` token as a Bearer Token, and hit your Gateway endpoints (`https://localhost:8243/your-api-context/1.0.0/...`). You will receive the mocked responses defined in your OAS.
* **LLM Integration:** Connect an LLM (like Claude Desktop or Cursor) to the generated MCP Server endpoint using the generated API Keys to let the AI interact with your mock APIs natively.

## ⚙️ Under the Hood

This project leverages:
* `wso2am-4.6.0.zip` base distribution.
* `apictl` (WSO2 CLI tool) for artifact initialization and status management.
* WSO2 Publisher & DevPortal Native REST APIs for deployment, application creation, and token generation.
* Embedded `Python 3` for precise YAML manipulation and MCP translation.
* `jq` for JSON payload parsing during the CI/CD bash script execution.

---
*Created for fast-paced API Development, QA Sandboxing, and AI/LLM Integration Demos.*