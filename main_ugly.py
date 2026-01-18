import os
from fastapi import FastAPI
from azure.storage.blob import BlobServiceClient
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

app = FastAPI(title="AI Agent - The OLD Way (Secrets Everywhere!)")

# ⚠️ WARNING: This is the "UGLY" version with all the anti-patterns!
# This shows what NOT to do in production

# ANTI-PATTERN #1: Hardcoded secrets (even worse than env vars!)
# In the real "ugly" version, developers might hardcode secrets like:
# STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=..."
# AZURE_OPENAI_API_KEY = "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# But we've removed them here to pass GitHub's push protection!

# ANTI-PATTERN #2: Reading from environment (better than hardcoding, but still dangerous)
STORAGE_CONNECTION_STRING = os.getenv("STORAGE_CONNECTION_STRING")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# ANTI-PATTERN #3: No validation - what if these are None?
# The app will crash with cryptic errors at runtime

def get_context_from_blob():
    """
    PROBLEMS WITH THIS APPROACH:
    1. Connection string is a GOD-MODE credential
    2. Can read, write, delete EVERYTHING in the storage account
    3. No expiration - lasts forever
    4. If leaked, requires emergency rotation across ALL environments
    5. Developers copy this to their laptops, CI/CD configs, etc.
    """
    # Using the dangerous connection string
    blob_service = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
    
    blob_client = blob_service.get_container_client("docs").get_blob_client("knowledge.txt")
    return blob_client.download_blob().readall().decode('utf-8')

@app.get("/ask")
async def ask_langchain(question: str):
    """
    PROBLEMS WITH THIS APPROACH:
    1. API key is static - never expires
    2. No audit trail of who's using it
    3. If a developer leaves, they still have the key on their laptop
    4. Key rotation requires updating code in 10+ places
    5. If key leaks to GitHub, it's scraped by bots in minutes
    """
    
    # Using the dangerous API key
    llm = AzureChatOpenAI(
        azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        openai_api_version="2024-02-15-preview",
        openai_api_key=AZURE_OPENAI_API_KEY  # 🚨 DANGER: Static secret!
    )

    # The RAG Chain (this part is fine, but it's built on a foundation of secrets)
    context = get_context_from_blob()
    
    prompt = ChatPromptTemplate.from_template("""
    Answer the question based only on the following context:
    {context}
    
    Question: {question}
    """)

    chain = prompt | llm | StrOutputParser()

    # Execute
    answer = await chain.ainvoke({"context": context, "question": question})
    return {
        "answer": answer, 
        "engine": "LangChain + API Key (INSECURE!)",
        "warning": "⚠️ This app uses hardcoded secrets. DO NOT USE IN PRODUCTION!"
    }

# ANTI-PATTERN #4: No error handling
# ANTI-PATTERN #5: No logging (how do you debug when things break?)
# ANTI-PATTERN #6: No health checks
# ANTI-PATTERN #7: Secrets likely committed to Git history
# ANTI-PATTERN #8: No way to revoke access without breaking the app
# ANTI-PATTERN #9: Same secrets used across dev, staging, and production
# ANTI-PATTERN #10: Developers share secrets via Slack/Email

"""
WHY THIS IS TERRIBLE:

1. SECRET SPRAWL:
   - .env files on developer laptops
   - CI/CD pipeline variables
   - Kubernetes secrets
   - Docker Compose files
   - Staging environment configs
   - Production environment configs
   - Backup scripts
   - Each copy is a potential leak point

2. KEY ROTATION NIGHTMARE:
   When you rotate the OpenAI key, you need to update:
   - Every developer's .env file
   - CI/CD secrets
   - Kubernetes secrets (kubectl apply)
   - Helm values files
   - Terraform variables
   - And you have 0 visibility into who has old keys cached

3. NO AUDIT TRAIL:
   - Who accessed the data? You don't know, everyone uses the same key
   - When did they access it? No visibility
   - What did they access? No logging

4. BLAST RADIUS = INFINITE:
   - If this key leaks, attacker has full access to:
     * All blobs in the storage account (read, write, delete)
     * All OpenAI deployments (can rack up $100k in charges)
     * No way to limit damage without breaking production

5. COMPLIANCE NIGHTMARE:
   - SOC2 audit: "Show me your secret rotation policy"
   - GDPR audit: "Show me who accessed customer data"
   - You can't answer these questions

THE SOLUTION: Workload Identity (see main.py)
- Zero secrets in code
- Cryptographic proof of identity
- Short-lived tokens (60 min expiration)
- Full audit trail
- Revoke access in real-time
- Least privilege (blast radius = tiny)
"""
