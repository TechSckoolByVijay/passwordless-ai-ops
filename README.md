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
- Azure Container Registry (ACR)
- Azure Kubernetes Service (AKS) - optional for deployment

### Azure Container Registry Setup

To enable AKS to pull images from ACR without passing secrets:

```bash
az aks update -g rg-sec-ops-agents -n aks-genai-agents --attach-acr demoacr
```

### Push Docker Image to ACR

```bash
# Build the Docker image
docker build -t passwordless-ai-ops-app:v1 .

# Login to ACR
docker login demoacr.azurecr.io -u demoacr -p "YOUR_ACR_PASSWORD"

# Tag the image
docker tag passwordless-ai-ops-app:v1 demoacr.azurecr.io/passwordless-ai-ops-app:v1

# Push to ACR
docker push demoacr.azurecr.io/passwordless-ai-ops-app:v1
```

> **Note**: Replace `demoacr` with your ACR name and use your actual ACR credentials.

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
# Build and push to ACR
az acr build --registry <your-acr> --image passwordless-ai-ops:latest .

# Deploy to ACI with Managed Identity
az container create \
  --resource-group <your-rg> \
  --name passwordless-ai-ops \
  --image <your-acr>.azurecr.io/passwordless-ai-ops:latest \
  --assign-identity \
  --environment-variables USE_MANAGED_IDENTITY=true \
  --ports 8000
```

### Using Azure Kubernetes Service (AKS)

```bash
# Apply Kubernetes deployment
kubectl apply -f aks-deployment.yaml
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
