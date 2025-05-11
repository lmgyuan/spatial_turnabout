import re
import os

def check_prompt_template():
    """Check the format of the verifier prompt template"""
    verifier_prompt_path = "data/aceattorney_data/scripts/Yuan/coding_verifier/verifier_prompt.txt"
    
    if not os.path.exists(verifier_prompt_path):
        print(f"Error: Verifier prompt file not found: {verifier_prompt_path}")
        return
    
    with open(verifier_prompt_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Find all placeholders in the format {name}
    placeholders = re.findall(r'\{([^}]+)\}', template)
    
    print("Placeholders found in the template:")
    for placeholder in set(placeholders):
        print(f"- {placeholder}")
    
    print("\nTemplate content:")
    print(template[:300] + "..." if len(template) > 300 else template)

if __name__ == "__main__":
    check_prompt_template() 