# Student Guide: Building Secret-less GenAI Applications with Azure Workload Identity

## 📚 Masterclass Overview

**Duration:** 40 minutes  
**Level:** Intermediate to Advanced  
**Prerequisites:** Basic knowledge of Kubernetes, Azure, and Python  

---

## 🎯 Learning Objectives

By the end of this masterclass, you will be able to:

1. ✅ Understand the security risks of secret-based authentication in GenAI applications
2. ✅ Explain how Azure Workload Identity provides passwordless authentication
3. ✅ Configure AKS clusters with OIDC Issuer and Workload Identity
4. ✅ Create Managed Identities and Federated Credentials
5. ✅ Apply Least Privilege RBAC to limit blast radius
6. ✅ Deploy a production-ready RAG agent without any secrets in code

---

## 📋 What You'll Build

A **LangChain-based RAG Agent** that:
- Runs on Azure Kubernetes Service (AKS)
- Reads documents from Azure Blob Storage
- Uses Azure OpenAI for natural language processing
- **Contains ZERO secrets in code, environment variables, or configuration files**

---

## 🛠️ Prerequisites & Setup

### Required Tools
- [ ] Azure CLI installed ([Download](https://docs.microsoft.com/cli/azure/install-azure-cli))
- [ ] kubectl installed ([Download](https://kubernetes.io/docs/tasks/tools/))
- [ ] Docker installed ([Download](https://docs.docker.com/get-docker/))
- [ ] VS Code or your preferred code editor
- [ ] Git for version control

### Required Azure Resources
- [ ] Active Azure subscription
- [ ] Azure Container Registry (ACR)
- [ ] Azure Kubernetes Service (AKS) cluster
- [ ] Azure Storage Account with a container named `docs`
- [ ] Azure OpenAI resource with a deployed model
- [ ] Upload `knowledge.txt` to your storage account's `docs` container

### Login to Azure
```bash
az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

---

## 📖 Part 1: Understanding the Problem (0:00 - 0:12)

### The $50 Million Security Incident

**Key Concept:** Every API key or connection string you create becomes a permanent security liability.

### The Lifecycle of a Secret (The Problem)

| Day | Event | Impact |
|-----|-------|--------|
| **Day 1** | Developer copies OpenAI API key to `.env` file | Secret created |
| **Day 30** | `.env` accidentally committed to GitHub | Secret leaked publicly |
| **Day 45** | Key rotated for compliance | Must update in 5+ places |
| **Day 90** | Developer leaves company | They still have the secret on their laptop |

### What is "Secret Sprawl"?

Secrets must be stored in multiple locations:
- ❌ Developer laptops (`.env` files)
- ❌ CI/CD pipeline variables
- ❌ Kubernetes secrets
- ❌ Docker Compose files
- ❌ Staging environment configs
- ❌ Production environment configs
- ❌ Backup scripts

**Each copy is a potential leak point!**

### 🔴 The Traditional "Ugly" Code

```python
# ANTI-PATTERN: Environment-based secrets
STORAGE_CONNECTION_STRING = os.getenv("STORAGE_CONNECTION_STRING")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

# God-mode credential with unlimited access
blob_service = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)

# Static API key that never expires
llm = AzureChatOpenAI(
    openai_api_key=AZURE_OPENAI_API_KEY  # 🚨 DANGER!
)
```

**Problems:**
- Connection string grants read/write/delete access to EVERYTHING
- API key never expires
- No audit trail of who accessed what
- Key rotation requires updating code in multiple places

---

## 📖 Part 2: The Solution - Azure Workload Identity (0:12 - 0:18)

### The Paradigm Shift

| Old Model (Human-Trust) | New Model (Machine-Verification) |
|------------------------|----------------------------------|
| Trust a secret because a human created it | Use cryptographic proof of identity |
| Secrets stored in code/config | No secrets anywhere |
| Manual key rotation | Automatic token refresh |
| Permanent credentials | Short-lived tokens (60 min) |
| One secret = unlimited access | Scoped permissions per identity |

### The Three Pillars of Workload Identity

#### 1️⃣ **OIDC Issuer** (Digital Notary)
- Built into your Kubernetes cluster
- Issues unique tokens to each pod
- Token contains: Pod name, namespace, cluster ID
- Acts as proof of identity

#### 2️⃣ **Managed Identity** (Service Passport)
- Created in Azure Active Directory
- Has NO password
- Purely cryptographic
- Can be assigned Azure RBAC permissions

#### 3️⃣ **Federated Credential** (Trust Bridge)
- Links Kubernetes Service Account to Azure Managed Identity
- Scopes trust to specific namespace and service account
- Only pods matching the criteria can use the identity

### How It Works (The Flow)

```
┌─────────────────┐
│  Pod starts up  │
│  in AKS cluster │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Azure Workload Identity webhook     │
│ injects OIDC token into pod         │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Pod presents OIDC token to Azure AD │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Azure AD validates token against    │
│ Federated Credential                │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Azure AD issues short-lived access  │
│ token (valid 60 minutes)            │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Pod uses access token to call       │
│ Azure OpenAI, Storage, etc.         │
└─────────────────────────────────────┘
```

**Key Benefits:**
- ✅ No secrets in code or environment
- ✅ Tokens expire automatically in 60 minutes
- ✅ Full audit trail in Azure AD
- ✅ Instant permission revocation
- ✅ No manual key rotation needed

---

## 🔧 Part 3: Hands-On Setup (0:18 - 0:31)

### Step 1: Attach ACR to AKS (Secret-less Image Pulls)

**Why:** Allow your AKS cluster to pull images from ACR without Docker credentials.

```bash
az aks update \
    --resource-group rg-sec-ops-agents \
    --name aks-genai-agents \
    --attach-acr demoacr
```

**What this does:**
- Uses Kubelet Managed Identity (cluster's built-in identity)
- No need to create `imagePullSecrets` in Kubernetes
- Consistent with the "no secrets" philosophy

---

### Step 2: Enable Workload Identity on AKS

```bash
az aks update \
    -g rg-sec-ops-agents \
    -n aks-genai-agents \
    --enable-oidc-issuer \
    --enable-workload-identity
```

**What this enables:**
- `--enable-oidc-issuer`: Creates the digital notary
- `--enable-workload-identity`: Activates the webhook that injects tokens

⏱️ **Expected time:** ~2 minutes

---

### Step 3: Create the Managed Identity

```bash
az identity create \
    --name id-ai-agent-identity \
    --resource-group rg-sec-ops-agents
```

**What you created:**
- A passwordless identity in Azure AD
- Currently has ZERO permissions (by design)
- Think of it as a service passport with no stamps yet

---

### Step 4: Create the Trust Bridge (Federated Credential)

```bash
# Get the OIDC issuer URL from your cluster
export AKS_OIDC_ISSUER="$(az aks show \
    -n aks-genai-agents \
    -g rg-sec-ops-agents \
    --query 'oidcIssuerProfile.issuerUrl' \
    -otsv)"

# Create the federated credential
az identity federated-credential create \
    --name "fed-identity-ai-agent" \
    --identity-name "id-ai-agent-identity" \
    --resource-group rg-sec-ops-agents \
    --issuer "${AKS_OIDC_ISSUER}" \
    --subject "system:serviceaccount:default:ai-agent-sa"
```

**Understanding the `subject` field:**

```
system:serviceaccount:default:ai-agent-sa
│                      │       │
│                      │       └─ Service Account name
│                      └───────── Kubernetes namespace
└──────────────────────────────── Kubernetes identifier
```

**This means:** "Azure, only trust this identity when presented by the service account `ai-agent-sa` in the `default` namespace."

---

### Step 5: Grant Least Privilege Permissions

#### Permission 1: Read from Storage

```bash
# Get the client ID of your managed identity
export USER_CLIENT_ID=$(az identity show \
    -g rg-sec-ops-agents \
    -n id-ai-agent-identity \
    --query clientId \
    -otsv)

# Grant Storage Blob Data Reader role
az role assignment create \
    --role "Storage Blob Data Reader" \
    --assignee $USER_CLIENT_ID \
    --scope /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RG/providers/Microsoft.Storage/storageAccounts/YOUR_STORAGE_ACCOUNT
```

**Why "Storage Blob Data Reader"?**

| Role | Can Read | Can Write | Can Delete | Can Manage Access |
|------|----------|-----------|------------|-------------------|
| Owner | ✅ | ✅ | ✅ | ✅ |
| Contributor | ✅ | ✅ | ✅ | ❌ |
| Storage Blob Data Contributor | ✅ | ✅ | ❌ | ❌ |
| **Storage Blob Data Reader** | ✅ | ❌ | ❌ | ❌ |

**Blast Radius:** If compromised, attacker can only READ the knowledge.txt file. They cannot delete your data lake.

#### Permission 2: Use Azure OpenAI

```bash
az role assignment create \
    --role "Cognitive Services OpenAI User" \
    --assignee $USER_CLIENT_ID \
    --scope /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RG/providers/Microsoft.CognitiveServices/accounts/YOUR_OPENAI_ACCOUNT
```

**Why "Cognitive Services OpenAI User"?**

| Permission | Included? |
|------------|-----------|
| Send prompts and get completions | ✅ |
| View billing | ❌ |
| Delete models | ❌ |
| Change rate limits | ❌ |
| Create new deployments | ❌ |

**Blast Radius:** If compromised, attacker can ask GPT questions. They CANNOT rack up $50k in charges by creating new deployments.

---

## 💻 Part 4: The Identity-Aware Code (0:31 - 0:37)

### Key Imports

```python
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.storage.blob import BlobServiceClient
from langchain_openai import AzureChatOpenAI
```

### The Magic: DefaultAzureCredential

```python
credential = DefaultAzureCredential()
```

**What makes this special:**

| Environment | Authentication Method Used |
|-------------|----------------------------|
| Your laptop | Your personal Azure login (via `az login`) |
| Azure Kubernetes | Workload Identity (pod's managed identity) |
| Azure Functions | Function's Managed Identity |
| Azure App Service | App Service's Managed Identity |

**One line of code. Works everywhere. No if-statements.**

### Authenticating to Azure OpenAI

```python
# Create a token provider function (not a string!)
token_provider = get_bearer_token_provider(
    credential,
    'https://cognitiveservices.azure.com/.default'
)

# Pass the function to LangChain
llm = AzureChatOpenAI(
    azure_deployment='gpt-5.2-chat',
    azure_endpoint='https://your-endpoint.cognitiveservices.azure.com/',
    openai_api_version="2024-02-15-preview",
    azure_ad_token_provider=token_provider  # Function, not a string!
)
```

**How it works:**
1. Every time LangChain needs to call OpenAI, it calls `token_provider()`
2. The function presents the pod's OIDC token to Azure AD
3. Azure AD returns a fresh access token (valid 60 min)
4. LangChain uses that token for the API call

**No API key. No manual rotation. Just works.**

### Authenticating to Azure Storage

```python
blob_service = BlobServiceClient(
    account_url='https://chatwithdata01.blob.core.windows.net/',
    credential=credential
)

blob_client = blob_service.get_container_client("docs").get_blob_client("knowledge.txt")
content = blob_client.download_blob().readall().decode('utf-8')
```

**Notice:**
- No connection string
- Just the URL and the credential
- Same pattern everywhere

---

## 🚀 Part 5: Kubernetes Deployment (0:37 - 0:43)

### The ServiceAccount

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ai-agent-sa
  namespace: default
  annotations:
    # This links K8s ServiceAccount to Azure Managed Identity
    azure.workload.identity/client-id: "YOUR_CLIENT_ID_HERE"
```

**Replace `YOUR_CLIENT_ID_HERE` with:**
```bash
az identity show -g rg-sec-ops-agents -n id-ai-agent-identity --query clientId -otsv
```

### The Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-agent-deploy
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai-agent
  template:
    metadata:
      labels:
        app: ai-agent
        # This triggers token injection
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: ai-agent-sa
      containers:
      - name: ai-agent
        image: demoacr.azurecr.io/passwordless-ai-ops-app:v10
        env:        
        - name: USE_MANAGED_IDENTITY
          value: "true"
        - name: STORAGE_ACCOUNT_URL
          value: "https://chatwithdata01.blob.core.windows.net/"
        - name: AZURE_OPENAI_ENDPOINT
          value: "https://your-openai.cognitiveservices.azure.com/"
        - name: AZURE_OPENAI_DEPLOYMENT_NAME
          value: "gpt-5.2-chat"
        ports:
        - containerPort: 8000
```

**Key observations:**
- ✅ `azure.workload.identity/use: "true"` → Enables token injection
- ✅ `serviceAccountName: ai-agent-sa` → Links to the ServiceAccount
- ✅ Environment variables contain ONLY URLs and names
- ✅ **ZERO secrets in this YAML file**
- ✅ This file can be committed to public GitHub!

### The Service (LoadBalancer)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: ai-agent-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: ai-agent
```

### Deploy to AKS

```bash
# Apply the deployment
kubectl apply -f aks-deployment.yaml

# Check pod status
kubectl get pods

# View logs
kubectl logs -l app=ai-agent

# Get external IP
kubectl get service ai-agent-service
```

**Expected logs:**
```
🔧 Configuration: USE_MANAGED_IDENTITY=True
✅ DefaultAzureCredential initialized for Managed Identity authentication
🔐 Using Managed Identity to access storage
📂 Accessing container: 'docs', blob: 'knowledge.txt'
✅ Successfully downloaded blob. Size: 1477 characters
🚀 Sending request to Azure OpenAI...
✅ Received response from Azure OpenAI
```

---

## 🧪 Part 6: Testing & The Kill Switch Demo (0:43 - 0:47)

### Test the API

1. **Get the external IP:**
```bash
kubectl get service ai-agent-service
# Note the EXTERNAL-IP column
```

2. **Open Swagger UI:**
```
http://EXTERNAL-IP/docs
```

3. **Test a question:**
```
Question: A non-profit school has 450 students and wants our 15% discount. 
What is their yearly cost and what is the catch?
```

**Expected Answer:**
```json
{
  "answer": "$1,020/year. The catch is they must sign a 3-year Legacy Contract.",
  "engine": "LangChain + Managed Identity"
}
```

### The "Kill Switch" Demo

**Scenario:** An employee leaves the company. How fast can you revoke their access?

#### Step 1: Delete the role assignment

```bash
# In Azure Portal:
# 1. Go to Storage Account → Access Control (IAM)
# 2. Find role assignment for "id-ai-agent-identity"
# 3. Click Delete
```

Or via CLI:
```bash
az role assignment delete \
    --assignee $USER_CLIENT_ID \
    --role "Storage Blob Data Reader" \
    --scope /subscriptions/.../storageAccounts/chatwithdata01
```

#### Step 2: Try the API again (immediately)

**Result:**
```json
{
  "detail": "ResourceNotFound: This request is not authorized..."
}
```

**Observations:**
- ✅ Failed **instantly** (no propagation delay)
- ✅ Pod still running (no restart needed)
- ✅ Identity still exists (only permission revoked)
- ✅ No secrets to invalidate

#### Step 3: Restore the permission

```bash
az role assignment create \
    --role "Storage Blob Data Reader" \
    --assignee $USER_CLIENT_ID \
    --scope /subscriptions/.../storageAccounts/chatwithdata01
```

#### Step 4: Try the API again

**Result:** ✅ Works again! The application automatically fetched a new token.

**This is self-healing security.**

---

## ✅ Part 7: Production Checklist (0:47 - 0:52)

### Before Going to Production

- [ ] **Enable OIDC Issuer and Workload Identity** on all AKS clusters
- [ ] **Create dedicated Managed Identities** per application (never share)
- [ ] **Use Federated Credentials** scoped to exact namespace and service account
- [ ] **Apply Least Privilege RBAC** (never use Owner or Contributor roles)
- [ ] **Implement comprehensive logging** to audit identity interactions
- [ ] **Test the kill switch** in non-prod to verify blast radius
- [ ] **Use Azure Policy** to enforce no secrets in pod specs or ConfigMaps
- [ ] **Monitor with Azure Monitor** for unusual identity activity

### Common Mistakes to Avoid

| ❌ Don't Do This | ✅ Do This Instead |
|------------------|-------------------|
| Use Kubelet Managed Identity for app access | Create dedicated Managed Identity per app |
| Store client IDs in Kubernetes secrets | Put them in ConfigMaps or pod labels (they're not sensitive) |
| Use wildcards in federated credential subjects | Always specify exact namespace and service account |
| Assign permissions at subscription level | Scope to resource groups or individual resources |
| Share one identity across multiple apps | One identity per application |

### Migration Strategy (For Existing Apps)

If you have applications currently using secrets:

**Phase 1: Dual-Mode Deployment (Week 1)**
```python
USE_MANAGED_IDENTITY = os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true"

if USE_MANAGED_IDENTITY:
    # New path: Workload Identity
    credential = DefaultAzureCredential()
else:
    # Old path: Connection strings
    # Keep this as fallback during migration
```

**Phase 2: Parallel Running (Weeks 2-3)**
- Deploy new version with `USE_MANAGED_IDENTITY=false`
- Verify functionality matches old version
- Monitor for errors

**Phase 3: Switch Over (Week 4)**
- Set `USE_MANAGED_IDENTITY=true`
- Monitor closely for 1 week
- Keep old code path as emergency rollback

**Phase 4: Cleanup (Week 5)**
- Remove the toggle and old code path
- Delete secrets from Key Vault/environment
- Update CI/CD pipelines to remove secret injection

---

## 🎯 Key Takeaways

### The Five Core Principles

1. **Secrets are liabilities** — Every API key you create becomes a permanent security risk

2. **Workload Identity replaces secrets with cryptographic trust** — No passwords, just math

3. **Federated Credentials scope identities** — Only specific pods can use specific identities

4. **Least Privilege RBAC limits blast radius** — Even compromised identities can't destroy your cloud

5. **Identity-aware code is simpler** — No key rotation logic, no secret management boilerplate

### The Impact at Scale

| Scenario | With Secrets | With Workload Identity |
|----------|--------------|------------------------|
| 50 GenAI apps with 5 secrets each | 250 secrets to manage | 0 secrets |
| Developer leaves company | Hunt for .env files on laptop | Revoke in Azure AD (1 click) |
| Key rotation | Update 10+ places | Automatic (tokens expire in 60 min) |
| Compliance audit | Show secret rotation logs | Show Azure AD audit logs |
| Security incident | Forensics on who has the key | Exact audit trail in Azure Monitor |

---

## 📚 Additional Resources

### Official Documentation
- [Azure Workload Identity Overview](https://learn.microsoft.com/azure/aks/workload-identity-overview)
- [DefaultAzureCredential Documentation](https://learn.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential)
- [Azure RBAC Roles](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles)

### GitHub Repository
- **Full Code:** https://github.com/TechSckoolByVijay/passwordless-ai-ops
- **Includes:**
  - Complete Python code (`main.py`)
  - Kubernetes manifests (`aks-deployment.yaml`)
  - Dockerfile
  - README with detailed instructions
  - "Ugly" version showing anti-patterns (`main_ugly.py`)

### Recommended Next Steps

1. **Deploy this in your sandbox** by the end of the week
2. **Identify one existing application** in your organization that uses secrets and migrate it
3. **Share this approach with your team** — especially your security engineers
4. **Practice the "kill switch" demo** to understand instant permission revocation

---

## ❓ FAQ

**Q: Can I use Workload Identity with Azure Functions or App Service?**  
A: Yes! Those services use Managed Identity (same concept, different implementation). The code remains identical thanks to `DefaultAzureCredential`.

**Q: What happens if the OIDC token leaks?**  
A: It expires in 60 minutes automatically. Plus, it only works from the specific pod/namespace it was issued to.

**Q: Do I need to restart pods after changing RBAC permissions?**  
A: No! Permissions are checked in real-time. Tokens are fetched fresh every 60 minutes.

**Q: Can I use this with on-premises Kubernetes?**  
A: No, this is Azure-specific. For AWS, look at IRSA (IAM Roles for Service Accounts). For GCP, look at Workload Identity Federation.

**Q: What if I need to access resources outside Azure?**  
A: You can still use Managed Identity to fetch secrets from Azure Key Vault as a secure middle layer, but the third-party API will still require a secret.

**Q: Is this more expensive than using secrets?**  
A: No additional cost! Managed Identities and Workload Identity are free Azure features.

---

## 🏆 Challenge: Your Homework

### Challenge 1: Basic (30 minutes)
- Deploy the provided code to your own AKS cluster
- Test the API with a question from your own knowledge base
- Perform the "kill switch" demo

### Challenge 2: Intermediate (2 hours)
- Add Azure Key Vault to the architecture
- Store the knowledge base in Key Vault instead of Blob Storage
- Use Managed Identity to access Key Vault

### Challenge 3: Advanced (4 hours)
- Migrate one of your existing applications to use Workload Identity
- Implement the dual-mode toggle for safe migration
- Document the before/after blast radius

---

## 📝 Notes Section

Use this space during the lecture to capture:
- Your specific subscription IDs and resource names
- Questions to ask during Q&A
- Ideas for applying this in your organization

```
My Subscription ID: _________________________________

My Resource Group: _________________________________

My Storage Account: _________________________________

My OpenAI Resource: _________________________________

My AKS Cluster: _________________________________

Notes:
__________________________________________________
__________________________________________________
__________________________________________________
__________________________________________________
```

---

## 🔐 Final Thought

> "In 2026, **security is not a bolt-on feature**. It's the foundation. Workload Identity isn't just about preventing leaks—it's about building systems that are **secure by design**."

**Let's build secret-less!** 🚀

---

*This guide is part of the TechSckool masterclass series. For more resources, visit: https://github.com/TechSckoolByVijay/passwordless-ai-ops*
