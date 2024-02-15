import openai
import backoff

@backoff.on_exception(backoff.expo, (openai.error.RateLimitError, openai.error.APIError, openai.error.Timeout, openai.error.ServiceUnavailableError))
#def run_chatgpt(message, model, force_json=False, temperature=0):
def run_chatgpt(message, model, temperature=0):
    if model == "gpt-4":
        openai.api_key = open(f'../../_private/harry_ccb.key').read()
    elif model == "gpt-3.5-turbo":
        openai.api_key = open(f'../../_private/harry_personal.key').read()

    #output_format = "json_object" if force_json else "text"
    ret = openai.ChatCompletion.create(
        model=model,
        messages=message,
        max_tokens = 100,
        #response_format = {"type": output_format}
    )
    gen_text = dict(ret["choices"][0]["message"])["content"]
    return gen_text