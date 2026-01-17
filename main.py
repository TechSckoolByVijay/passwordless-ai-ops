import os
from fastapi import FastAPI
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

app = FastAPI(title="Pro-Grade Identity AI Agent")

# Configuration: Toggle between Managed Identity and Connection String
USE_MANAGED_IDENTITY = os.getenv("USE_MANAGED_IDENTITY", "true").lower() == "true"

# 1. Identity Setup
credential = DefaultAzureCredential() if USE_MANAGED_IDENTITY else None

def get_context_from_blob():
    """Fetches private data from Azure Blob with or without managed identity."""
    if USE_MANAGED_IDENTITY:
        # Using Managed Identity (passwordless)
        blob_url = os.getenv("STORAGE_ACCOUNT_URL")
        blob_service = BlobServiceClient(account_url=blob_url, credential=credential)
    else:
        # Using Connection String (with secrets)
        connection_string = os.getenv("STORAGE_CONNECTION_STRING")
        blob_service = BlobServiceClient.from_connection_string(connection_string)
    
    # Using a simple file read for the 1-hour demo
    blob_client = blob_service.get_container_client("docs").get_blob_client("knowledge.txt")
    return blob_client.download_blob().readall().decode('utf-8')

@app.get("/ask")
async def ask_langchain(question: str):
    # 2. Initialize LangChain with Managed Identity or API Key
    if USE_MANAGED_IDENTITY:
        # Using Managed Identity (passwordless)
        llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            openai_api_version="2024-02-15-preview",
            # This is the "Magic" - telling LangChain to use our Azure Identity
            azure_ad_token_provider=credential.get_token("https://cognitiveservices.azure.com/.default").token
        )
        auth_method = "Managed Identity"
    else:
        # Using API Key (with secrets)
        llm = AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            openai_api_version="2024-02-15-preview",
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY")
        )
        auth_method = "API Key"

    # 3. The RAG Chain
    context = get_context_from_blob()
    
    prompt = ChatPromptTemplate.from_template("""
    Answer the question based only on the following context:
    {context}
    
    Question: {question}
    """)

    chain = prompt | llm | StrOutputParser()

    # 4. Execute
    answer = await chain.ainvoke({"context": context, "question": question})
    return {"answer": answer, "engine": f"LangChain + {auth_method}"}