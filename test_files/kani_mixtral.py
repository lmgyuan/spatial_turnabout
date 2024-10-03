import asyncio
import torch
from kani import Kani
from kani.engines.huggingface.llama2 import LlamaEngine
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3-8B")

# Set the pad_token to eos_token if not already set
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Load mixtral in fp16
common_hf_model_args = dict(
    device_map="auto",
    torch_dtype=torch.float16,
)

engine = LlamaEngine(
    # "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "meta-llama/Meta-Llama-3-8B",
    max_context_size=8192,
    model_load_kwargs=common_hf_model_args,
    do_sample=True,
    temperature=0.6,
    top_p=0.9,
)

def truncate_query(query, max_length):
    input_ids = tokenizer.encode(query, return_tensors="pt")
    if input_ids.size(1) > max_length:
        input_ids = input_ids[:, :max_length]
        query = tokenizer.decode(input_ids[0], skip_special_tokens=True)
    return query                                          

# Query mixtral
async def query_one(query):
    query = truncate_query(query, 8192)
    ai = Kani(engine)
    resp = await ai.chat_round_str(query)
    print(resp)
    return resp
    

async def main():
    # Load queries here
    queries = ["How many connections does each stop on the Yamanote Line have?"]
    for query in queries:
        resp = await query_one(query)
        # Save response here

if __name__ == "__main__":
    asyncio.run(main())

