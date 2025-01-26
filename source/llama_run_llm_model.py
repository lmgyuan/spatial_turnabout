import asyncio
from transformers import pipeline
import os

# Load the model and initialize the pipeline
model_name = "google/gemma-2-9b"
cache_dir = "/nlp/data/huggingface_cache"
hf_pipeline = pipeline("text-generation", model=model_name, device=0, cache_dir=cache_dir)  # Use device=0 for GPU

async def run_model(model_name: str, prompt: str) -> str:
    """
    Runs the LLaMA 3.1-8b model using Hugging Face's pipeline with the given prompt and returns the response.
    """
    # Define a synchronous function to run the pipeline
    def generate_output():
        return hf_pipeline(prompt, max_length=1024, do_sample=True, use_auth_token=True, temperature=0.7)[0]["generated_text"]

    # Run the synchronous generation in an async-friendly way
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, generate_output)

    print(f"Generated response: {response}")
    return response

