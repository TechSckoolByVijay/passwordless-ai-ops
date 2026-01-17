import os
import logging
from fastapi import FastAPI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.storage.blob import BlobServiceClient
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pro-Grade Identity AI Agent")

# Configuration: Toggle between Managed Identity and Connection String
USE_MANAGED_IDENTITY = os.getenv("USE_MANAGED_IDENTITY", "true").lower() == "true"
logger.info(f"🔧 Configuration: USE_MANAGED_IDENTITY={USE_MANAGED_IDENTITY}")

# 1. Identity Setup
credential = DefaultAzureCredential() if USE_MANAGED_IDENTITY else None
if USE_MANAGED_IDENTITY:
    logger.info("✅ DefaultAzureCredential initialized for Managed Identity authentication")

def get_context_from_blob():
    """Fetches private data from Azure Blob with or without managed identity."""
    logger.info("📦 Starting blob storage access...")
    
    if USE_MANAGED_IDENTITY:
        # Using Managed Identity (passwordless)
        blob_url = os.getenv("STORAGE_ACCOUNT_URL")
        logger.info(f"🔐 Using Managed Identity to access storage: {blob_url}")
        blob_service = BlobServiceClient(account_url=blob_url, credential=credential)
    else:
        # Using Connection String (with secrets)
        connection_string = os.getenv("STORAGE_CONNECTION_STRING")
        logger.info(f"🔑 Using Connection String to access storage")
        blob_service = BlobServiceClient.from_connection_string(connection_string)
    
    # Using a simple file read for the 1-hour demo
    container_name = "docs"
    blob_name = "knowledge.txt"
    logger.info(f"📂 Accessing container: '{container_name}', blob: '{blob_name}'")
    
    blob_client = blob_service.get_container_client(container_name).get_blob_client(blob_name)
    
    logger.info("⬇️ Downloading blob content...")
    blob_data = blob_client.download_blob().readall().decode('utf-8')
    logger.info(f"✅ Successfully downloaded blob. Size: {len(blob_data)} characters")
    logger.debug(f"📄 Blob content preview: {blob_data[:200]}...")
    
    return blob_data

@app.get("/ask")
async def ask_langchain(question: str):
    logger.info(f"🎯 Received question: '{question}'")
    
    # 2. Initialize LangChain with Managed Identity or API Key
    if USE_MANAGED_IDENTITY:
        # Using Managed Identity (passwordless)
        logger.info("🔐 Initializing Azure OpenAI with Managed Identity...")
        # Create a token provider function that returns tokens on-demand
        token_provider = get_bearer_token_provider(
            credential,
            "https://cognitiveservices.azure.com/.default"
        )
        logger.info("✅ Token provider created successfully")
        
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        logger.info(f"🤖 Azure OpenAI Config - Endpoint: {endpoint}, Deployment: {deployment}")
        
        llm = AzureChatOpenAI(
            azure_deployment=deployment,
            azure_endpoint=endpoint,
            openai_api_version="2024-02-15-preview",
            azure_ad_token_provider=token_provider
        )
        auth_method = "Managed Identity"
    else:
        # Using API Key (with secrets)
        logger.info("🔑 Initializing Azure OpenAI with API Key...")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        logger.info(f"🤖 Azure OpenAI Config - Endpoint: {endpoint}, Deployment: {deployment}")
        
        llm = AzureChatOpenAI(
            azure_deployment=deployment,
            azure_endpoint=endpoint,
            openai_api_version="2024-02-15-preview",
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY")
        )
        auth_method = "API Key"

    logger.info(f"✅ LLM initialized with {auth_method}")

    # 3. The RAG Chain
    logger.info("🔄 Fetching context from blob storage...")
    context = get_context_from_blob()
    logger.info(f"✅ Context retrieved. Length: {len(context)} characters")
    
    logger.info("📝 Building prompt template...")
    prompt = ChatPromptTemplate.from_template("""
    Answer the question based only on the following context:
    {context}
    
    Question: {question}
    """)

    # Format the complete prompt before sending
    formatted_prompt = prompt.format(context=context, question=question)
    logger.info("=" * 80)
    logger.info("📤 COMPLETE PROMPT BEING SENT TO AZURE OPENAI:")
    logger.info("=" * 80)
    logger.info(formatted_prompt)
    logger.info("=" * 80)

    chain = prompt | llm | StrOutputParser()
    logger.info("✅ LangChain pipeline assembled")

    # 4. Execute
    logger.info("🚀 Sending request to Azure OpenAI...")
    answer = await chain.ainvoke({"context": context, "question": question})
    logger.info(f"✅ Received response from Azure OpenAI. Answer length: {len(answer)} characters")
    logger.debug(f"📄 Answer preview: {answer[:200]}...")
    
    response = {"answer": answer, "engine": f"LangChain + {auth_method}"}
    logger.info("✅ Request completed successfully")
    
    return response