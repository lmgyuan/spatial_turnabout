import numpy as np
import asyncio

VALUE_PROMPT = """
Evaluate the following response based on how well it addresses the original prompt. Respond with a single number between 0 and 10, where higher numbers indicate better responses. 
Don't response anything other than a number.

Example:
Original Prompt: 1+1=
Response: 2
Evaluation Score: 10

Original Prompt: {prompt}
Response: {response}
Evaluation Score:
"""

GENERATE_PROMPT = """
You are solving a problem step by step. The original problem is:
{original_prompt}

The current state of the solution is:
{current_state}

Generate the next step in the solution. Be creative and consider multiple approaches before finalizing your answer.

Next Step:
"""

async def tot(prompt, ai, n_generate_sample=2, n_evaluate_sample=1, n_select_sample=1, steps=2, temperature=0.6):
    """
    Synchronous Tree of Thought (ToT) solver that generates, evaluates, and selects the best response.
    """
    # Input validation
    if n_generate_sample <= 0 or n_evaluate_sample <= 0 or n_select_sample <= 0 or steps <= 0:
        raise ValueError("All sampling and step parameters must be greater than 0.")

    ys = [prompt]  # Initialize candidates with the initial prompt
    history = []

    for step in range(steps):
        print(f"\nStep {step+1}/{steps}")
        # Step 1: Generate new candidates
        new_ys = []
        for y in ys:
            current_state = y if step > 0 else ""
            generate_prompts = [
                GENERATE_PROMPT.format(original_prompt=prompt, current_state=current_state) 
                for _ in range(n_generate_sample)
            ]
            responses = [await ai.chat_round_str(generate_prompt, temperature=temperature)
                         for generate_prompt in generate_prompts]
            new_ys.extend(responses)

        print(f"Generated {len(new_ys)} candidates:")
        for i, y in enumerate(new_ys, 1):
            preview = y
            print(f"  {i}. {preview}")
        
        # Step 2: Evaluate candidates
        values = []
        for y in new_ys:
            eval_prompts = [VALUE_PROMPT.format(prompt=prompt, response=y) for _ in range(n_evaluate_sample)]
            eval_responses = [await ai.chat_round_str(eval_prompt, temperature=temperature)
                              for eval_prompt in eval_prompts]
            eval_scores = []
            for eval_response in eval_responses:
                if not eval_response.strip():  # Check if response is empty
                    print(f"Empty evaluation response. Defaulting to 0.")
                    eval_scores.append(0)
                    continue
                try:
                    score = float(eval_response.strip().split()[-1])
                    eval_scores.append(score)
                except (ValueError, IndexError) as e:
                    print(f"Error parsing evaluation response: {e}. Response: '{eval_response}'. Defaulting to 0.")
                    eval_scores.append(0)
            value = np.mean(eval_scores)
            values.append(value)

        print("\nEvaluations:")
        for i, (y, value) in enumerate(zip(new_ys, values), 1):
            print(f"  {i}. Score: {value:.2f}")
        
        # Step 3: Select top candidates
        if n_select_sample < len(new_ys):
            sorted_indices = np.argsort(values)[-n_select_sample:]
            ys = [new_ys[i] for i in sorted_indices]
        else:
            ys = new_ys

        print(f"\nSelected best response (score: {max(values):.2f}):")
        print(f"  {ys[0][:100]}...")
        print("-" * 50)
        
        # Log history
        history.append({
            'step': step,
            'candidates': new_ys,
            'values': values,
            'selected': ys
        })
    
    return ys[0], history