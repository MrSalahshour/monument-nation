import pandas as pd
import google.generativeai as genai
import os
import time
from dotenv import load_dotenv
from google.api_core import exceptions

# SETUP
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

genai.configure(api_key=API_KEY)


MODEL_NAME = 'gemma-3-4b-it' 
model = genai.GenerativeModel(MODEL_NAME)

INPUT_FILE = 'paris_monuments_verified.csv'
OUTPUT_FILE = 'paris_monuments_llm_verified.csv'

def llm_verify_equivalence(input_name, wiki_name, description, category):
    """
    Uses Gemini to check if input_name and wiki_name refer to the same place.
    """
    prompt = f"""
    You are a data validation assistant for a monuments dataset.
    I have an original input name for a location and a Wikipedia page found for it.
    
    Task: Determine if the 'Input Name' and the 'Wiki Name' refer to the EXACT same real-world place or attraction, considering the description and category.
    
    Input Name: "{input_name}"
    Wiki Name: "{wiki_name}"
    Wiki Description: "{description}"
    Category: "{category}"
    
    If they are the same place (even if the spelling differs slightly or one is a sub-section of the other), answer "TRUE".
    If they are different places, different branches, or completely unrelated, answer "FALSE".
    
    Answer strictly with just the word: TRUE or FALSE.
    """
    
    try:
        response = model.generate_content(prompt)
        answer = response.text.strip().upper()
        
        if "TRUE" in answer:
            return True
        elif "FALSE" in answer:
            return False
        else:
            print(f"  [!] Ambiguous LLM response for '{input_name}': {answer}")
            return False
            
    except exceptions.ResourceExhausted:
        print("  [!] Rate limit hit. Sleeping for 60 seconds...")
        time.sleep(60)
        return llm_verify_equivalence(input_name, wiki_name, description, category) # Retry
    except Exception as e:
        print(f"  [!] Error validating '{input_name}': {e}")
        return False

def main():
    print(f"Loading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)

    # Filter: Rows that are marked False AND have missing coordinates
    # We create a mask for rows that need checking
    rows_to_check = (df['is_correct'] == False) & (df['lat'].isna() | df['lon'].isna())
    
    count_to_check = rows_to_check.sum()
    print(f"Found {count_to_check} samples requiring LLM verification.")
    print(f"Using model: {MODEL_NAME}")
    print("-" * 40)

    # Counters
    verified_as_true = 0
    processed = 0

    # Iterate only over the specific rows
    for index, row in df[rows_to_check].iterrows():
        processed += 1
        
        i_name = row['input_name']
        w_name = row['wiki_name']
        desc = row.get('wiki_description', '')
        cat = row.get('category', '')

        print(f"[{processed}/{count_to_check}] Checking: '{i_name}' vs '{w_name}'...", end=" ")

        is_equivalent = llm_verify_equivalence(i_name, w_name, desc, cat)
        
        if is_equivalent:
            print("MATCH (True)")
            df.at[index, 'is_correct'] = True
            verified_as_true += 1
        else:
            print("MISMATCH (False)")
            # It remains False, so no change needed, but explicit for clarity
            # df.at[index, 'is_correct'] = False 

        # Rate limiting: Sleep 4 seconds between requests to stay safe 
        # (15 requests/min = 1 req every 4 seconds)
        time.sleep(4.0)

    # Save results
    print("-" * 40)
    print("LLM Verification Complete.")
    print(f"Total checked: {count_to_check}")
    print(f"Recovered (changed to True): {verified_as_true}")
    
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Updated dataset saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()