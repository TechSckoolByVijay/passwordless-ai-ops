# Passwordless AI Ops - Azure Identity Demo

A FastAPI application demonstrating **passwordless authentication** with Azure services using Managed Identity and Workload Identity, featuring LangChain RAG (Retrieval-Augmented Generation) with Azure OpenAI.

## Features

- 🔐 **Toggle Authentication Modes**: Switch between Managed Identity (passwordless) and API keys/connection strings
- 🤖 **AI-Powered Q&A**: LangChain RAG pipeline with Azure OpenAI
- 📦 **Azure Blob Storage**: Secure document retrieval
- 🐳 **Docker Ready**: Containerized application with Docker Compose
- ⚙️ **Environment-Based Configuration**: Easy setup with `.env` file

## Architecture

```
┌─────────────────┐
│   FastAPI App   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│ Azure │ │  Azure  │
│ Blob  │ │ OpenAI  │
└───────┘ └─────────┘
```

## Prerequisites

- Docker & Docker Compose
- Azure Storage Account with a container named `docs` containing `knowledge.txt`
- Azure OpenAI resource with a deployed model
- Azure Container Registry (ACR) - optional for AKS deployment
- Azure Kubernetes Service (AKS) - optional for deployment

### Push Docker Image to ACR

```bash
# Build the Docker image
docker build -t passwordless-ai-ops-app:v1 .

```

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/TechSckoolByVijay/passwordless-ai-ops.git
cd passwordless-ai-ops
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
# Authentication Mode: true for Managed Identity, false for API Keys
USE_MANAGED_IDENTITY=false

# Azure Storage (when USE_MANAGED_IDENTITY=false)
STORAGE_CONNECTION_STRING=your_storage_connection_string

# Azure Storage (when USE_MANAGED_IDENTITY=true)
STORAGE_ACCOUNT_URL=https://youraccount.blob.core.windows.net

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name

# Azure Identity (when USE_MANAGED_IDENTITY=true)
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
```

### 3. Run with Docker Compose

```bash
docker-compose up --build
```

The application will be available at `http://localhost:8000`

### 4. Test the API

**API Documentation**: `http://localhost:8000/docs`

**Ask a Question**:
```bash
curl "http://localhost:8000/ask?question=What is the pricing for Pro tier?"
```

## Authentication Modes

### Mode 1: Connection Strings & API Keys (Development)

Set in `.env`:
```bash
USE_MANAGED_IDENTITY=false
```

- Uses connection strings for Azure Storage
- Uses API keys for Azure OpenAI
- ⚠️ **Not recommended for production** (secrets in environment)

### Mode 2: Managed Identity (Production)

Set in `.env`:
```bash
USE_MANAGED_IDENTITY=true
```

- Uses Azure Managed Identity / Workload Identity
- No secrets needed in code or environment
- ✅ **Recommended for production** (zero-trust security)

## Project Structure

```
passwordless-ai-ops/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container image definition
├── docker-compose.yml     # Docker Compose configuration
├── knowledge.txt          # Sample knowledge base
├── .env                   # Environment variables (not tracked)
├── .gitignore            # Git ignore file
└── README.md             # This file
```

## API Endpoints

### `GET /ask`

Ask a question based on the knowledge base stored in Azure Blob Storage.

**Parameters**:
- `question` (query parameter): Your question

**Response**:
```json
{
  "answer": "The Pro tier costs $1,200/yr...",
  "engine": "LangChain + API Key"
}
```

## Technologies Used

- **FastAPI**: Modern Python web framework
- **LangChain**: AI orchestration framework
- **Azure OpenAI**: GPT models for natural language processing
- **Azure Blob Storage**: Document storage
- **Azure Identity**: Passwordless authentication
- **Docker**: Containerization

## Deployment to Azure

### Using Azure Container Instances (ACI)

```bash
# Build the Docker image
docker build -t passwordless-ai-ops-app:latest .

# Login to ACR
az acr login --name <your-acr>

# Tag the image for ACR
docker tag passwordless-ai-ops-app:latest <your-acr>.azurecr.io/passwordless-ai-ops-app:latest

# Push to ACR
docker push <your-acr>.azurecr.io/passwordless-ai-ops-app:latest

# Deploy to ACI with Managed Identity
az container create \
  --resource-group <your-rg> \
  --name passwordless-ai-ops \
  --image <your-acr>.azurecr.io/passwordless-ai-ops-app:latest \
  --assign-identity \
  --environment-variables USE_MANAGED_IDENTITY=true \
  --ports 8000
```

> **Note**: Replace `<your-acr>` and `<your-rg>` with your actual ACR name and resource group.

### Using Azure Kubernetes Service (AKS)

#### Step 1: Attach ACR to AKS

Enable AKS to pull images from ACR without passing secrets:

```bash
az aks update \
    -g rg-sec-ops-agents \
    -n aks-genai-agents \
    --attach-acr demoacr
```

#### Step 2: Enable Workload Identity on Your Cluster

If your AKS cluster is already created, you need to enable the OIDC issuer and Workload Identity features:

```bash
# Update your existing cluster to enable Workload Identity
az aks update \
    -g rg-sec-ops-agents \
    -n aks-genai-agents \
    --enable-oidc-issuer \
    --enable-workload-identity
```

#### Step 3: Create the Managed Identity & Trust Bridge

Create the Managed Identity and establish the trust relationship between Kubernetes and Azure:

```bash
# 1. Create the Managed Identity
az identity create \
    --name id-ai-agent-identity \
    --resource-group rg-sec-ops-agents

# 2. Get the OIDC Issuer URL (required for the trust handshake)
export AKS_OIDC_ISSUER="$(az aks show -n aks-genai-agents -g rg-sec-ops-agents --query "oidcIssuerProfile.issuerUrl" -otsv)"

# 3. Create the Federated Credential
# This establishes trust: "Azure, trust the Service Account 'ai-agent-sa' in the 'default' namespace"
az identity federated-credential create \
    --name "fed-identity-ai-agent" \
    --identity-name "id-ai-agent-identity" \
    --resource-group rg-sec-ops-agents \
    --issuer "${AKS_OIDC_ISSUER}" \
    --subject "system:serviceaccount:default:ai-agent-sa"
```

#### Step 4: Grant Least Privilege Permissions

Assign the managed identity the minimum required permissions to access Azure resources:

```bash
# Get the Client ID of your managed identity
export USER_CLIENT_ID=$(az identity show -g rg-sec-ops-agents -n id-ai-agent-identity --query clientId -otsv)

# Grant Storage Blob Data Reader role (for accessing knowledge.txt)
az role assignment create \
    --role "Storage Blob Data Reader" \
    --assignee $USER_CLIENT_ID \
    --scope /subscriptions/db8fcd00-4f68-42c3-8b19-947bf4d7b2c5/resourceGroups/chatwithdata/providers/Microsoft.Storage/storageAccounts/chatwithdata01

# Grant Cognitive Services OpenAI User role (for Azure OpenAI access)
az role assignment create \
    --role "Cognitive Services OpenAI User" \
    --assignee $USER_CLIENT_ID \
    --scope /subscriptions/db8fcd00-4f68-42c3-8b19-947bf4d7b2c5/resourceGroups/rg-sec-ops-agents/providers/Microsoft.CognitiveServices/accounts/vijay-mkiemtgq-swedencentral
```

> **Note**: Replace the subscription ID, resource group names, and resource names with your actual Azure resources.

#### Step 5: Deploy to AKS

```bash
# Apply Kubernetes deployment
kubectl apply -f aks-deployment.yaml

# Verify the deployment
kubectl get pods
kubectl get service ai-agent-service

# Check logs
kubectl logs -l app=ai-agent

# Restart deployment if needed (after RBAC changes)
kubectl rollout restart deployment/ai-agent-deploy
```

#### Step 6: Test the Deployed Application

```bash
# Get the external IP of the service
kubectl get service ai-agent-service

# Test the API (replace <EXTERNAL-IP> with actual IP)
curl "http://<EXTERNAL-IP>/ask?question=What is the pricing for Pro tier?"
```

## Security Best Practices

✅ **Do:**
- Use Managed Identity in production
- Store secrets in Azure Key Vault
- Enable Azure RBAC for access control
- Use private endpoints for Azure services

❌ **Don't:**
- Commit `.env` files to version control
- Hardcode API keys or connection strings
- Use root user in containers
- Expose services without authentication

## Troubleshooting

### Error: "The specified container does not exist"
- Ensure you have a container named `docs` in your Azure Storage Account
- Upload `knowledge.txt` to the `docs` container

### Error: "Access denied due to invalid subscription key"
- Verify your Azure OpenAI API key is correct
- Check that the endpoint URL is in the format: `https://your-resource.openai.azure.com/`
- Ensure the deployment name matches your Azure OpenAI deployment

### Error: "Resource not found (404)"
- Verify your `AZURE_OPENAI_DEPLOYMENT_NAME` matches the actual deployment name in Azure

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use this project for learning and production purposes.

## Contact

**TechSckool By Vijay**
- GitHub: [@TechSckoolByVijay](https://github.com/TechSckoolByVijay)
