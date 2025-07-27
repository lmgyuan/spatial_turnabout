"""
Model loader module for shared functionality between run_models_spatial.py and run_models_parallel.py
"""

import json
import os
from dotenv import load_dotenv
from openai import OpenAI

def load_model(model, config_path="models.json"):
    """
    Load a model client based on the model name and configuration.
    Currently supports OpenAI and Nebius models only.
    
    Args:
        model (str): Model name or identifier
        config_path (str): Path to the models configuration file
        
    Returns:
        tuple: (client, name) where client is the model client object and name is the model name
        
    Raises:
        ValueError: If the model is not supported (not OpenAI or Nebius)
    """
    with open(config_path, 'r') as file:
        config = json.load(file)
    
    # Store original model key for type detection
    original_model = model
    
    # Resolve model name from config
    model = config.get(model, model)
    
    # Check if model is supported (OpenAI or Nebius only)
    is_openai = any(m_name in original_model for m_name in ["gpt", "o3", "o4"])
    is_nebius = "nebius" in original_model
    
    if not (is_openai or is_nebius):
        supported_models = "OpenAI models (gpt-*, o3-*, o4-*) and Nebius models (nebius-*)"
        raise ValueError(f"Unsupported model: '{original_model}'. Currently supported: {supported_models}")
    
    # Load environment variables
    load_dotenv("../.env")
    
    # Determine provider
    if is_openai:
        model_key = "openai"
    elif is_nebius:
        model_key = "nebius"
    else:
        # This should never happen due to the check above, but keeping for safety
        raise ValueError(f"Unexpected model type: {original_model}")
    
    # Configure authentication
    auth = {
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "name": model
        },
        "nebius": {
            "api_key": os.getenv("NEBIUS_API_KEY"),
            "base_url": "https://api.studio.nebius.com/v1/",
            "name": model
        }
    }
    
    # Validate API key exists
    api_key = auth[model_key]["api_key"]
    if not api_key:
        raise ValueError(f"{model_key.upper()}_API_KEY environment variable not set")
    
    # Create client
    if "base_url" in auth[model_key]:
        client = OpenAI(
            api_key=api_key,
            base_url=auth[model_key]["base_url"]
        )
    else:
        client = OpenAI(
            api_key=api_key,
        )
    
    name = auth[model_key]["name"]
    
    return client, name 