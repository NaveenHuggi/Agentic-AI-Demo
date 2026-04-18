import os
import warnings
import logging

# Suppress litellm's verbose internal logging
os.environ["LITELLM_LOG"] = "ERROR"
warnings.filterwarnings("ignore")
logging.getLogger("LiteLLM").setLevel(logging.ERROR)
logging.getLogger("litellm").setLevel(logging.ERROR)
logging.getLogger("LiteLLM Router").setLevel(logging.ERROR)
logging.getLogger("LiteLLM Proxy").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("openai").setLevel(logging.ERROR)
logging.getLogger("chromadb").setLevel(logging.ERROR)

import litellm
litellm.suppress_debug_info = True
litellm.set_verbose = False

from litellm import Router
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

# Helper function to dynamically harvest all numbered API keys from the environment
def get_keys_by_prefix(prefix: str) -> list:
    keys = []
    for k, v in os.environ.items():
        if k.startswith(prefix) and v.strip():
            keys.append(v.strip())
    # If the user only defined a standard single key without numbers (e.g. GROQ_API_KEY)
    if not keys and os.environ.get(prefix):
        keys.append(os.environ.get(prefix))

    # Support GOOGLE_API_KEY as an alias for GEMINI_API_KEY
    if prefix == "GEMINI_API_KEY" and not keys and os.environ.get("GOOGLE_API_KEY"):
        keys.append(os.environ.get("GOOGLE_API_KEY"))
    
    # Return empty list if no keys found, omit the dummy "" key
    return keys

# Gather all arsenals of keys
github_keys = get_keys_by_prefix("GITHUB_API_KEY")
groq_keys = get_keys_by_prefix("GROQ_API_KEY")
gemini_keys = get_keys_by_prefix("GEMINI_API_KEY")
sambanova_keys = get_keys_by_prefix("SAMBANOVA_API_KEY")

model_list = []

# ========================================================
# HIGH-THROUGHPUT MULTIPLEXING ENGINE
# We inject EVERY single key as an independent routing node
# ========================================================

# Distribute load across all GitHub Keys (Master Primary)
for key in github_keys:
    model_list.append({
        "model_name": "master_model",
        "litellm_params": {"model": "github/gpt-4o", "api_key": key}
    })

# Distribute load across all SambaNova Keys (Master Secondary)
for key in sambanova_keys:
    model_list.append({
        "model_name": "master_model",
        "litellm_params": {"model": "openai/DeepSeek-R1", "api_key": key, "api_base": "https://api.sambanova.ai/v1"}
    })

# Distribute load across all Groq Keys (Workers & Critiques & Master Fallback)
for key in groq_keys:
    # Master Fallback
    model_list.append({
        "model_name": "master_model",
        "litellm_params": {"model": "groq/llama-3.3-70b-versatile", "api_key": key}
    })
    # Workers
    model_list.append({
        "model_name": "worker_model",
        "litellm_params": {"model": "groq/llama-3.3-70b-versatile", "api_key": key}
    })
    # Critiques
    model_list.append({
        "model_name": "critique_model",
        "litellm_params": {"model": "groq/llama-3.3-70b-versatile", "api_key": key}
    })

# Distribute load across all Gemini Keys (Observer & Fallbacks)
for key in gemini_keys:
    model_list.append({
        "model_name": "observer_model",
        "litellm_params": {"model": "gemini/gemini-flash-latest", "api_key": key}
    })
    # Also add Gemini as fallback for workers and master if no other keys exist
    if not groq_keys and not github_keys and not sambanova_keys:
        model_list.append({
            "model_name": "master_model",
            "litellm_params": {"model": "gemini/gemini-flash-latest", "api_key": key}
        })
        model_list.append({
            "model_name": "worker_model",
            "litellm_params": {"model": "gemini/gemini-flash-latest", "api_key": key}
        })
        model_list.append({
            "model_name": "critique_model",
            "litellm_params": {"model": "gemini/gemini-flash-latest", "api_key": key}
        })

# Instantiate the Router with Automatic Key Rotation
llm_router = Router(
    model_list=model_list,
    # 'simple-shuffle' activates True Key Rotation (Load Balancing)
    # It randomly picks from available keys, artificially increasing your TPM/RPM throughput
    routing_strategy="simple-shuffle",
    
    # If the randomly picked key hits a 429 Rate Limit, seamlessly retry with a different key
    num_retries=3,
    
    # Allow 1 failure per minute to drop the key lower in priority without crashing
    allowed_fails=1 
)

def query_llm(role_model: str, messages: list) -> str:
    """
    Queries the multiplexed LiteLLM Router for a specific abstracted role.
    """
    print(f"[Gateway] Load-Balancing request for role: {role_model} across available keys...")
    try:
        response = llm_router.completion(
            model=role_model,
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[Gateway CRITICAL] Exhausted ALL rotational keys & fallbacks for {role_model}: {str(e)}")
        return "ERROR_IN_COMPLETION"

# --- LANGCHAIN ADAPTER ---

from langchain_community.chat_models.litellm_router import ChatLiteLLMRouter

def get_routed_llm(role: str = "worker_model", temperature: float = 0, **kwargs) -> ChatLiteLLMRouter:
    """
    Returns a LangChain-compatible wrapped BaseChatModel that routes 
    through LiteLLM's resilient, rate-limit bypassing router.
    """
    return ChatLiteLLMRouter(
        router=llm_router, 
        model_name=role,
        temperature=temperature,
        **kwargs
    )
