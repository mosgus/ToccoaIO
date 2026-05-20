from google import genai
import anthropic

''' API Init '''
gemini_model = "gemini-3.1-flash-lite-preview"
claude_model = "claude-haiku-4-5-20251001"

# Gemini Init
with open("./keys/gemini_key.txt", "r") as f:
    gem_key = f.read().strip()
    gem_client = genai.Client(api_key=gem_key)
# Anthropic Init
with open("./keys/claude_key.txt", "r") as f:
    claude_key = f.read().strip()
    claude_client = anthropic.Anthropic(api_key=claude_key)

''' API Tests '''
# Claude API test
try:
    init_response = claude_client.messages.create(
        model= claude_model,  max_tokens= 5,
        messages=[{"role": "user", "content": "Return 1 random emoji."}]
    )
    # Correct way to access the text in Anthropic's SDK
    response_text = init_response.content[0].text

    if len(response_text) > 0:
        print(f"Claude API connection confirmed: {response_text}")
    else: print("Claude: No response received.")
except Exception as e: print(f"Claude Error: {e}")
# Gemini API test
try:
    init_response = gem_client.models.generate_content(
        model= gemini_model,
        contents="Return 1 random emoji."
    )
    if len(init_response.text) > 0:
        print(f"Gemini API connection confirmed: {init_response.text}")
    else: print("No response received.")
except Exception as e: print(f"Gemini Error: {e}")