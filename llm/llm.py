import os
import time
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import RunnableConfig

load_dotenv()


def _is_token_limit_error(error_text: str) -> bool:
    text = error_text.lower()
    patterns = [
        "context length exceeded",
        "maximum context length",
        "max context length",
        "context window",
        "prompt is too long",
        "request too large",
        "too many tokens",
        "token limit",
        "input too long",
        "413",
    ]
    return any(p in text for p in patterns)


def _is_rate_limit_error(error_text: str) -> bool:
    text = error_text.lower()
    patterns = [
        "rate limit",
        "too many requests",
        "429",
    ]
    return any(p in text for p in patterns)


def get_llm(tools=None, structured_model=None):
    """
    Initializes the LLM with automatic fallback across multiple models.

    Behavior:
    - If a model hits token/context limit -> switch immediately to the next model
    - If a model hits rate limit -> wait briefly, retry once, then switch if needed
    - Preserves tools / structured output bindings for each fallback model
    - Passes RunnableConfig through the chain so tracing/callbacks still work
    """
    provider = "groq"

    models = [
        os.getenv("LLM_MODEL_1", "llama-3.3-70b-versatile"),
        os.getenv("LLM_MODEL_2", "mixtral-8x7b-32768"),
        os.getenv("LLM_MODEL_3", "llama3-70b-8192"),
    ]
    models = [m for m in models if m]

    if not models:
        raise RuntimeError("No LLM models configured.")

    runnables = []
    for model_name in models:
        llm = init_chat_model(
            model=model_name,
            model_provider=provider,
            temperature=0,
            max_retries=0,  # handled manually here
        )

        if tools:
            llm = llm.bind_tools(tools)

        if structured_model:
            llm = llm.with_structured_output(structured_model)

        runnables.append((model_name, llm))

    def _execute_with_fallback(messages, config: RunnableConfig | None = None):
        last_error = None

        for attempt, (model_name, runnable) in enumerate(runnables):
            if attempt > 0:
                print(f"\n[LLM Switch] Switching to fallback model: '{model_name}'")

            try:
                return runnable.invoke(messages, config=config)

            except Exception as e:
                last_error = str(e)
                print(f"[LLM Error] Model '{model_name}' failed: {last_error[:300]}")

                if _is_token_limit_error(last_error):
                    print(f"[Token Limit] '{model_name}' exceeded its context/token limit. Trying next model...")
                    continue

                if _is_rate_limit_error(last_error):
                    print(f"[Rate Limit] '{model_name}' hit rate limits. Waiting 5 seconds, then retrying once...")
                    time.sleep(5)

                    try:
                        return runnable.invoke(messages, config=config)
                    except Exception as retry_error:
                        last_error = str(retry_error)
                        print(f"[Retry Failed] Model '{model_name}' still failed: {last_error[:300]}")
                        print(f"[Fallback] Moving to next model...")
                        continue

                # Any other error -> move to next model
                print(f"[Fallback] Non-recoverable error on '{model_name}'. Trying next model...")
                continue

        print("\n[FATAL] All models in the fallback chain were exhausted.")
        raise RuntimeError(f"Fallback chain completely exhausted. Last error: {last_error}")

    return RunnableLambda(_execute_with_fallback)