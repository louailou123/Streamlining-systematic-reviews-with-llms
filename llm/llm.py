import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()

def get_llm():
    """
    Initializes the LLM from environment variables.
    Supports multiple providers (google_genai, groq, openai, etc.)
    
    Set in .env:
        LLM_MODEL=llama-3.3-70b-versatile
        LLM_PROVIDER=groq
        GROQ_API_KEY=your_key
    """
    model = os.getenv("LLM_MODEL", "gemini-2.5-flash-lite")
    provider = os.getenv("LLM_PROVIDER", "google_genai")

    # Make sure the right API key env var is set for each provider
    if provider == "google_genai":
        api_key =os.getenv("GEMINI_API_KEY")
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key

    return init_chat_model(
        model=model,
        model_provider=provider,
        temperature=0.1,
    )
