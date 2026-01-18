# Masterclass: Building Secret-less GenAI Applications with Azure Workload Identity

**Duration:** 40 minutes  
**Topic:** Zero-Trust AI Agents using AKS, LangChain, and Azure Workload Identity  
**Audience:** Cloud Engineers, DevOps, AI/ML Engineers  

---

## Part 1: The Hook - The $50 Million Security Incident (0:00 - 0:05)

**Visual:** Your face on camera, then cut to a slide showing leaked secrets headlines

**Script:**

"Welcome to this masterclass. Before we write a single line of code today, I want you to imagine this scenario:

It’s 3 AM. Your phone rings. Your CISO is on the line. Someone just pushed a commit to GitHub with an Azure OpenAI API key embedded in a .env file. That repository was public for 4 hours before anyone noticed. In those 4 hours, that key was scraped by bots and used to rack up $47,000 in OpenAI charges.Because the application relied entirely on password-based access, the blast radius wasn’t limited to OpenAI, the same .env file also exposed credentials for the Azure Storage Account, Key Vault, and the production database, all protected using passwords or static secrets, Attackers didn’t just burn tokens. They exfiltrated data, enumerated blobs, read secrets, and touched production databases.

But the real cost? The reputational damage. The customer data that was accessed. The emergency security audit. The total: Over $50 million.

This isn't fiction. Variants of this story happen every month in 2026. And here's the terrifying part: **a huge percentage of GenAI projects still begin with developers copy-pasting API keys into environment files.**

Today, we are building something different. A production-grade RAG agent that runs on Azure Kubernetes Service and accesses both private data and AI models **without a single password, API key, or connection string in the code.**

By the end of this session, you will understand why Workload Identity is not just a 'nice-to-have'—it's the **only acceptable way** to deploy modern GenAI workloads in 2026.

Let's begin."

---

## Part 2: The Traditional Approach - Understanding the Problem (0:05 - 0:12)

**Visual:** VS Code showing the "old way" with secrets everywhere

**Script:**

"Let me show you how most GenAI applications are built today. [Open main.py]

Here's a typical RAG pipeline using LangChain. What do we see?

```python
STORAGE_CONNECTION_STRING = os.getenv("STORAGE_CONNECTION_STRING")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
```

These look harmless, right? They're just environment variables. But let's trace the lifecycle of these secrets:

**Day 1:** Developer creates the Azure OpenAI resource, copies the key from the Portal, pastes it into .env file.

**Day 30:** .env file accidentally gets committed to GitHub because someone forgot to update .gitignore.

**Day 45:** The key gets rotated for compliance. Now you have to update it in 5 different places: Dev environment, Staging, Production, CI/CD pipeline, and the developer's local machine.

**Day 90:** A developer leaves the company. They still have that .env file on their laptop. You have no way to revoke their access without breaking production.

This is what I call **Secret Sprawl**. Every secret you create becomes a permanent liability.

Now, let me show you the connection string for Azure Storage. [Open .env file]

Look at this: `AccountKey=8U8KLgv...`. This is a **God-mode credential**. With this string, you can read, write, delete, and destroy an entire storage account. There's no expiration, no scope limitation.

If this leaks, you don't just have a security incident—you have a **business continuity crisis**.

The question we need to answer is: **How do we build GenAI applications without creating this liability?**

The answer is **Azure Workload Identity**. Let me show you how."

---

## Part 3: The Identity Revolution - From Keys to Cryptographic Trust (0:12 - 0:18)

**Visual:** Switch to Azure Portal and architecture diagram

**Script:**

"The fundamental shift we need to make is moving from **Human-Trust** to **Machine-Verification**.

In the old model, we trusted a secret because a human created it and secured it. In the new model, we use **cryptographic proof** that a specific workload is who it claims to be.

Here's how it works. [Show architecture diagram]

1. **OIDC Issuer**: Think of this as a digital notary inside your Kubernetes cluster. Every pod gets a unique token that says, 'I am Pod X running in Namespace Y on Cluster Z.'

2. **Managed Identity**: This is like a service passport. It's an identity in Azure Active Directory, but it has no password. It's purely cryptographic.

3. **Federated Credential**: This is the trust bridge. We tell Azure, 'Only accept tokens from this specific Kubernetes service account in this specific namespace on this specific cluster.'

The beauty of this system? **No secrets ever leave Azure**. When your pod needs to access OpenAI or Storage, it presents its OIDC token. Azure validates it cryptographically and issues a short-lived access token—valid for just 60 minutes.

If that token leaks? It expires automatically. No key rotation needed. No emergency 3 AM calls.

This is the **Zero-Trust** model. And it's not just secure—it's **operationally superior**.

Let me show you how to build this."

---

## Part 4: Live Setup - The Foundation (0:18 - 0:25)

**Visual:** Terminal showing Azure CLI commands

**Script:**

"Alright, let's build this from scratch. I'm going to show you the exact commands, and I'll explain what each one does.

**Step 1: Attach ACR to AKS for Secret-less Image Pulls**

Before we even talk about application identities, let's secure how our cluster pulls container images.

```bash
az aks update \
    -g rg-sec-ops-agents \
    -n aks-genai-agents \
    --attach-acr demoacr
```

[Execute command]

Notice what we just did? We gave our AKS cluster permission to pull images from Azure Container Registry **without needing to pass Docker credentials**. This uses the Kubelet Managed Identity—another form of passwordless auth.

In the old world, you'd create an image pull secret with Docker credentials. Those credentials would be stored in Kubernetes secrets. If they leaked or expired, your deployments would fail.

Now? The cluster uses its own identity to pull images. No secrets. No credentials. This is consistency—we're eliminating secrets at every layer.

**Step 2: Enable Workload Identity on the cluster**

```bash
az aks update \
    -g rg-sec-ops-agents \
    -n aks-genai-agents \
    --enable-oidc-issuer \
    --enable-workload-identity
```

[Execute command]

This command does two things:
- Enables the OIDC issuer, which creates that 'digital notary' I mentioned
- Activates Workload Identity support

This takes about 2 minutes. While this runs, let me explain the next step.

**Step 3: Create the Managed Identity**

```bash
az identity create \
    --name id-ai-agent-identity \
    --resource-group rg-sec-ops-agents
```

[Execute command]

I just created a password-less identity in Azure AD. This identity has **zero permissions** right now. It's just a digital passport.

**Step 4: Create the Trust Bridge**

Now comes the critical part—the federated credential.

```bash
export AKS_OIDC_ISSUER="$(az aks show -n aks-genai-agents -g rg-sec-ops-agents --query 'oidcIssuerProfile.issuerUrl' -otsv)"

az identity federated-credential create \
    --name "fed-identity-ai-agent" \
    --identity-name "id-ai-agent-identity" \
    --resource-group rg-sec-ops-agents \
    --issuer "${AKS_OIDC_ISSUER}" \
    --subject "system:serviceaccount:default:ai-agent-sa"
```

[Execute command]

Look at that subject field: `system:serviceaccount:default:ai-agent-sa`

This is saying: 'Azure, only trust this identity when it's presented by a Kubernetes service account named ai-agent-sa in the default namespace.'

This is **cryptographic scope limitation**. Even if someone somehow extracts the OIDC token, they can't use it outside this specific context.

No password. No secret. Just mathematical proof of identity."

---

## Part 5: Least Privilege - Surgical Precision Security (0:25 - 0:31)

**Visual:** Azure Portal showing IAM blade

**Script:**

"Now we have an identity, but it's powerless. This is intentional. In the Zero-Trust model, **nothing has access by default**.

We're going to use RBAC—Role-Based Access Control—to give our agent **exactly the minimum permissions it needs**. No more. No less.

**Permission 1: Read from Storage**

```bash
export USER_CLIENT_ID=$(az identity show -g rg-sec-ops-agents -n id-ai-agent-identity --query clientId -otsv)

az role assignment create \
    --role "Storage Blob Data Reader" \
    --assignee $USER_CLIENT_ID \
    --scope /subscriptions/.../storageAccounts/chatwithdata01
```

[Execute command]

I want you to notice something: **Storage Blob Data Reader**. Not Owner. Not Contributor. Not even 'Blob Data Contributor.'

This identity can **read blobs**. It cannot create them. It cannot delete them. It cannot modify access policies.

If this AI agent gets compromised—maybe through a prompt injection attack—the attacker can read our knowledge.txt file. That's it. They can't delete our entire data lake.

**Permission 2: Use Azure OpenAI**

```bash
az role assignment create \
    --role "Cognitive Services OpenAI User" \
    --assignee $USER_CLIENT_ID \
    --scope /subscriptions/.../accounts/vijay-mkiemtgq-swedencentral
```

[Execute command]

'Cognitive Services OpenAI User.' This role lets you send prompts and get completions. It does **not** let you:
- View billing
- Delete models
- Change rate limits
- Access other customers' data

If someone steals this identity's token, they can ask GPT questions. They cannot rack up $50,000 in charges by spinning up new deployments.

This is what I call **Blast Radius Engineering**. We assume breach. We limit damage.

Let's see this in action."

---

## Part 6: The Code - Identity-Aware Development (0:31 - 0:37)

**Visual:** VS Code showing main.py

**Script:**

"Now let's look at the application code. [Open main.py]

Look at the imports:

```python
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
```

`DefaultAzureCredential` is the Swiss Army knife of Azure authentication. Here's what makes it brilliant:

When I run this on **my laptop**, it uses my personal Azure login.
When this runs in **Azure Kubernetes**, it automatically detects Workload Identity and uses the pod's identity.
When you deploy this to **Azure Functions**, it uses the function's Managed Identity.

One line of code. Works everywhere. No if-statements. No environment detection logic.

Now look at how we authenticate to OpenAI:

```python
token_provider = get_bearer_token_provider(
    credential,
    'https://cognitiveservices.azure.com/.default'
)

llm = AzureChatOpenAI(
    azure_deployment='gpt-5.2-chat',
    azure_endpoint='https://...',
    azure_ad_token_provider=token_provider
)
```

Notice what's **missing**? No API key parameter. Instead, we pass a `token_provider`—a **function** that fetches fresh tokens on demand.

Every time LangChain calls OpenAI, it calls this function. The function goes to Azure AD and says, 'Hey, I'm this pod, here's my OIDC token as proof.' Azure responds with a fresh access token valid for 60 minutes.

Now look at the blob storage code:

```python
blob_service = BlobServiceClient(
    account_url='https://chatwithdata01.blob.core.windows.net/',
    credential=credential
)
```

Same pattern. No connection string. Just the URL and the credential.

**This is identity-aware code**. It's not just secure—it's **simpler**. No key rotation logic. No secret management boilerplate. Just business logic.

Let's deploy this."

---

## Part 7: Deployment & The Magic Moment (0:37 - 0:43)

**Visual:** Terminal showing kubectl commands, then browser with FastAPI docs

**Script:**

"The deployment is where everything comes together. [Open aks-deployment.yaml]

Look at the ServiceAccount:

```yaml
metadata:
  annotations:
    azure.workload.identity/client-id: "8f9cae76-2daa-426b-88f5-6e062aee5896"
```

This links our Kubernetes service account to our Azure Managed Identity. This is the glue.

Now look at the Pod spec:

```yaml
metadata:
  labels:
    azure.workload.identity/use: "true"
spec:
  serviceAccountName: ai-agent-sa
```

When we add that label, Azure's mutating webhook **automatically injects** environment variables and token files into our pod at runtime.

And look at the environment section:

```yaml
env:        
- name: USE_MANAGED_IDENTITY
  value: "true"
- name: STORAGE_ACCOUNT_URL
  value: "https://chatwithdata01.blob.core.windows.net/"
- name: AZURE_OPENAI_ENDPOINT
  value: "https://vijay-mkiemtgq-swedencentral.cognitiveservices.azure.com/"
```

**No secrets**. Just URLs. This YAML file can be committed to GitHub. It can be shared in Slack. It's **public information**.

Let's deploy:

```bash
kubectl apply -f aks-deployment.yaml
```

[Execute command]

```bash
kubectl get pods
kubectl logs -l app=ai-agent
```

[Show logs]

Look at the logs. See this?

```
🔐 Using Managed Identity to access storage
📂 Accessing container: 'docs', blob: 'knowledge.txt'
✅ Successfully downloaded blob. Size: 1477 characters
🚀 Sending request to Azure OpenAI...
✅ Received response from Azure OpenAI
```

It's working. Let's test it for real.

```bash
kubectl get service ai-agent-service
```

[Get external IP and open in browser at /docs]

Here's the FastAPI Swagger UI. I'm going to ask a question that requires reading our private knowledge base:

**Question:** 'A non-profit school has 450 students and wants our 15% discount. What is their yearly cost and what is the catch?'

[Execute the query]

[Wait for response]

Look at that! The agent:
1. Authenticated to Azure Storage using its Workload Identity
2. Downloaded the knowledge.txt file
3. Sent a prompt to Azure OpenAI (also using Workload Identity)
4. Returned a complete answer: '$1,020/year with the catch being a required 3-year Legacy Contract'

**All without a single secret in the code.**

Now, let me show you the 'kill switch.'"

---

## Part 8: The Kill Switch - Security in Action (0:43 - 0:47)

**Visual:** Azure Portal, then back to API testing

**Script:**

"This is my favorite part. [Open Azure Portal]

I'm going to the Storage Account IAM. I'm finding our managed identity's role assignment. And I'm deleting it.

[Delete the role assignment]

Now let's try that same API call again. [Switch to browser]

[Execute the same question]

[Wait for error]

```json
{
  "detail": "ResourceNotFound: This request is not authorized..."
}
```

**It failed instantly**. The identity still exists. The pod is still running. But the **permission was revoked in real-time**.

No key rotation. No pod restart. No secrets to invalidate.

This is the power of Identity-based security. When an employee leaves, you don't hunt for .env files on their laptop. You just revoke their identity's role assignments in Azure AD. **One click. Immediate effect.**

Let me restore that permission so our demo keeps working. [Re-add role assignment]

Now, one more test to show you the resilience. [Execute API call again]

It works again. The identity automatically fetched a new token. The application didn't need to restart. **This is self-healing security**."

---

## Part 9: The Production Checklist (0:47 - 0:52)

**Visual:** Slide showing checklist

**Script:**

"Before we wrap up, let me give you the production-readiness checklist for secret-less GenAI applications.

**✅ Checklist for Workload Identity Success:**

1. **Enable OIDC Issuer and Workload Identity** on your AKS cluster
2. **Create dedicated Managed Identities** per application—never share identities across workloads
3. **Use Federated Credentials** to scope the identity to specific namespaces and service accounts
4. **Apply Least Privilege RBAC**—never use Owner or Contributor roles
5. **Implement comprehensive logging** (like we did) so you can audit every identity interaction
6. **Test the kill switch**—actually delete role assignments in non-prod to verify your blast radius
7. **Use Azure Policy** to enforce that no secrets exist in pod specs or ConfigMaps
8. **Monitor with Azure Monitor** for unusual identity activity

**Common Mistakes to Avoid:**

❌ **Don't** use the Kubelet Managed Identity for application access—it's for cluster operations only
❌ **Don't** store identity client IDs in secrets—they're not sensitive, put them in ConfigMaps or pod labels
❌ **Don't** use wildcards in federated credential subjects—always specify exact namespace and service account
❌ **Don't** assign permissions at subscription level—scope to resource groups or individual resources

**Migration Strategy:**

If you have existing applications with secrets, here's the migration path:
1. Deploy the new identity-aware version **alongside** the secret-based version
2. Use a feature flag (like our USE_MANAGED_IDENTITY toggle) to switch between them
3. Run both in parallel for 2 weeks to verify stability
4. Once verified, delete the secrets and remove the legacy code path
5. Update your CI/CD pipelines to remove secret injection

This de-risks the migration and gives you a rollback option."

---

## Part 10: The Broader Picture - Why This Matters (0:52 - 0:57)

**Visual:** Architecture diagram showing enterprise scale

**Script:**

"Let me zoom out for a moment. This isn't just about securing one GenAI application. This is about **changing how we build cloud-native systems**.

In 2026, every company is becoming an AI company. You're not building one GenAI app—you're building 50. You're integrating LLMs into every workflow: customer support, document processing, code generation, data analysis.

If each of those applications has 5 secrets (OpenAI key, storage connection string, database password, etc.), you now have **250 secrets** to rotate, secure, and audit.

With Workload Identity, that number goes to **zero**. Not 10. Not 5. **Zero.**

This is what enables **GitOps at scale**. Your entire infrastructure—including GenAI applications—can be described in Git. No secrets in repos. No secrets in CI/CD variables. Just identity references.

This is what enables **zero-downtime key rotation**. When you need to rotate credentials, you revoke the role assignment, then re-add it. The application doesn't restart. Users don't notice.

This is what enables **regulatory compliance**. When an auditor asks, 'Show me your secret management process,' you say, 'We don't have secrets. We have identities, and here's the audit log of every access.'

This is the **competitive advantage** for 2026. Companies that embrace Workload Identity will ship GenAI features 10x faster because they're not fighting secret sprawl.

Companies that don't? They're one leaked API key away from a $50 million incident."

---

## Part 11: Q&A Preview & Resources (0:57 - 1:00)

**Visual:** Slide with QR code and GitHub repo link

**Script:**

"We've covered a lot in 40 minutes. Let me recap the key concepts:

1. **Secrets are liabilities**—every API key you create becomes a permanent security risk
2. **Workload Identity replaces secrets with cryptographic trust**—no passwords, just math
3. **Federated Credentials scope identities**—only specific pods can use specific identities
4. **Least Privilege RBAC limits blast radius**—even compromised identities can't destroy your cloud
5. **Identity-aware code is simpler**—no rotation logic, no secret management boilerplate

**What You Can Do Next:**

The entire codebase we built today—including the Kubernetes manifests, the Python code, and the CLI commands—is available on GitHub at:

**github.com/TechSckoolByVijay/passwordless-ai-ops**

I've also included a CLI Cheat Sheet with every command we ran, so you can replicate this in your environment.

**Three Challenges for You:**

1. **Deploy this in your sandbox** by the end of the week
2. **Identify one existing application** in your organization that still uses secrets and migrate it
3. **Share this approach with your team**—especially your security engineers—they'll love you for it

Before we open for questions, I want to leave you with one final thought:

In 2026, **security is not a bolt-on feature**. It's the foundation. Workload Identity isn't just about preventing leaks—it's about building systems that are **secure by design**.

Thank you for joining this masterclass. Let's build secret-less."

---

## Speaking Notes & Timing Guide

### Time Allocation (40 minutes total)
- **Part 1-2 (Hook + Problem):** 7 minutes
- **Part 3 (Identity Concept):** 6 minutes
- **Part 4 (Live Setup):** 7 minutes
- **Part 5 (RBAC):** 6 minutes
- **Part 6-7 (Code + Deploy):** 12 minutes
- **Part 8 (Kill Switch Demo):** 4 minutes
- **Part 9-11 (Checklist + Wrap):** 8 minutes

### Pacing Tips
1. **Slow down during CLI commands**—let people screenshot or copy commands
2. **Speed up during concept explanations**—people can rewatch, but live demos are precious
3. **Build suspense before the kill switch demo**—it's your wow moment

### Backup Plans
- If commands take too long, have pre-recorded terminal casts ready
- If the API call fails unexpectedly, have a backup video of it working
- If you finish early, expand Q&A or do the "migrate from secrets" live demo

### Emotional Beats
- **0-5 min:** Fear (the $50M incident)
- **5-18 min:** Hope (there's a better way)
- **18-37 min:** Empowerment (you can build this)
- **37-47 min:** Wonder (watch it actually work)
- **47-60 min:** Confidence (you're ready to ship this)

### Repeating Phrases (Use 3+ times)
- "No secrets. Just identities."
- "This is the Zero-Trust model."
- "Secure by design, not by luck."
- "Blast radius engineering."

### Visual Transitions
- Start with your face (build connection)
- Switch to VS Code for code walkthrough (tactical)
- Switch to Azure Portal for infrastructure (strategic)
- Switch to browser for live demo (proof)
- End with slides for recap (consolidation)
