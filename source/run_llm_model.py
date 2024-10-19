# run_llm_model.py
import os
import asyncio
from typing import List, Dict, Any
from openai import OpenAI
import aiohttp

# Load API keys from environment variables
# MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
# META_AI_API_KEY = os.getenv("META_AI_API_KEY")
OPENAI_API_KEY = "sk-ty5QEa2ORTuCZ9-LgIlnQW6CEFFjZ1D2iizKBxElSNT3BlbkFJk-26x0DWV2wROzdueAiSe5wq-cSRI5HqVLtimI2MIA"

# API endpoints
MISTRAL_API_URL = "https://api.mistral.ai/v1"
META_AI_API_URL = "https://api.meta.ai/v1"  # Placeholder URL, replace with actual endpoint

# Initialize OpenAI client
openai_client = OpenAI(
    organization='org-ZWMRC3KJT3026wx9IKBrgqU7',
    project='proj_KIj6goqeAJGtv3OeVj9yOyYn',
    api_key=OPENAI_API_KEY
)

#
# class SimpleAsyncClient:
#     def __init__(self, api_key: str, base_url: str):
#         self.session = aiohttp.ClientSession(
#             base_url=base_url,
#             headers={"Authorization": f"Bearer {api_key}"}
#         )
#
#     async def chat_completions_create(self, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
#         async with self.session.post(
#                 "/chat/completions",
#                 json={"model": model, "messages": messages}
#         ) as response:
#             return await response.json()
#
#     async def close(self):
#         await self.session.close()


# class MistralClient(SimpleAsyncClient):
#     def __init__(self):
#         super().__init__(MISTRAL_API_KEY, MISTRAL_API_URL)
#
#
# class MetaAIClient(SimpleAsyncClient):
#     def __init__(self):
#         super().__init__(META_AI_API_KEY, META_AI_API_URL)
#

# # Initialize clients
# mistral_client = MistralClient()
# meta_ai_client = MetaAIClient()


async def run_model(model_name: str, prompt: str) -> str:
    """
    Runs the specified LLM model with the given prompt and returns the response.
    """
    messages = [{"role": "user", "content": prompt}]

    # if model_name == "mixtral":
    #     response = await mistral_client.chat_completions_create(
    #         model="mistral-large-latest",
    #         messages=messages
    #     )
    #     return response["choices"][0]["message"]["content"]
    #
    # elif model_name == "llama":
    #     response = await meta_ai_client.chat_completions_create(
    #         model="llama-3-8b",
    #         messages=messages
    #     )
    #     return response["choices"][0]["message"]["content"]

    if model_name in ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]:
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=messages
        )
        return response.choices[0].message.content

    else:
        raise ValueError(f"Model {model_name} is not supported.")


# # Example usage
# async def main():
#     prompt = "Explain the concept of artificial intelligence in simple terms."
#     mixtral_response = await run_model("mixtral", prompt)
#     llama_response = await run_model("llama", prompt)
#     gpt_response = await run_model("gpt-3.5-turbo", prompt)
#
#     print("Mixtral response:", mixtral_response)
#     print("Llama response:", llama_response)
#     print("GPT-3.5 response:", gpt_response)
#
#     # Close clients
#     await mistral_client.close()
#     await meta_ai_client.close()
#
#
# if __name__ == "__main__":
#     asyncio.run(main())

# # Example usage
# async def main():
#     prompt = "Explain the concept of artificial intelligence in simple terms."
#     mixtral_response = await run_model("mixtral", prompt)
#     llama_response = await run_model("llama", prompt)
#     gpt_response = await run_model("gpt-3.5-turbo", prompt)
#
#     print("Mixtral response:", mixtral_response)
#     print("Llama response:", llama_response)
#     print("GPT-3.5 response:", gpt_response)
#
#
# if __name__ == "__main__":
#     asyncio.run(main())
#
#
# # Example usage
# async def main():
#     prompt = "Explain the concept of artificial intelligence in simple terms."
#     mixtral_response = await run_model("mixtral", prompt)
#     llama_response = await run_model("llama", prompt)
#     gpt_response = await run_model("gpt-3.5-turbo", prompt)
#
#     print("Mixtral response:", mixtral_response)
#     print("Llama response:", llama_response)
#     print("GPT-3.5 response:", gpt_response)
#
#
# if __name__ == "__main__":
#     asyncio.run(main())

# Manvi's codes
# import asyncio
# import torch
# from kani import Kani
# from kani.engines.huggingface.llama2 import LlamaEngine
#
# # Configure the Llama engine with Mixtral model
# common_hf_model_args = dict(
#     device_map="auto",
#     torch_dtype=torch.float16,
# )
#
# engine_mixtral= LlamaEngine(
#     "mistralai/Mixtral-8x7B-Instruct-v0.1",
#     max_context_size=32768,
#     model_load_kwargs=common_hf_model_args,
#     do_sample=False,
# )
# engine_llama = LlamaEngine(
#     "meta-llama/Meta-Llama-3-8B",
#     max_context_size=8192,
#     model_load_kwargs=common_hf_model_args,
#     do_sample=False,
# )
# '''
# engine_gemma = LlamaEngine(
#     "google/gemma-7b",
#     max_context_size=8192,
#     model_load_kwargs=common_hf_model_args,
#     do_sample=False,
# )
# '''
# async def run_model(model, past_dialogs, prompt):
#     if model == "mixtral":
#         engine = engine_mixtral
#     elif model == "llama":
#         engine = engine_llama
#     #  elif model == "gemma":
#         # engine = engine_gemma
#     ai = Kani(engine, chat_history=past_dialogs)
#     if past_dialogs:
#         last_user_message = past_dialogs[-1]['content']  # Assuming last entry is user's latest input
#     else:
#         last_user_message = ""
#     resp = await ai.chat_round_str(last_user_message)
#     return resp
#
