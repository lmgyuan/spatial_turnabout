import os
from kani import Kani
from kani.engines.huggingface import HuggingEngine
import asyncio
from argparse import ArgumentParser
parser = ArgumentParser()
parser.add_argument("--model", dest="model", help="Model name to use")


model_name = parser.parse_args().model
engine = HuggingEngine(model_id = model_name, use_auth_token=True, model_load_kwargs={"device_map": "auto"})
ai = Kani(engine, system_prompt="")


async def run_model():
    message = ["Which progressive metal band is the best?", "Which Japanese fusion band is the best?"]
    response = await ai.chat_round_str(message)
    print(response)


asyncio.run(run_model())
