import google.generativeai as genai

# PASTE YOUR KEY HERE
GENAI_KEY = "PASTE_YOUR_KEY_HERE"
genai.configure(api_key="AIzaSyDoH8xVNYHHV3_sAfxm-qtdQLqy7FHGEpU")

print("Checking available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error: {e}")