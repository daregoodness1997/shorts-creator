#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key:
    print("ERROR: GOOGLE_API_KEY not found in .env file")
    exit(1)

try:
    import google.generativeai as genai

    genai.configure(api_key=google_api_key)

    print("Available Gemini models:\n")
    for model in genai.list_models():
        if "generateContent" in model.supported_generation_methods:
            print(f"  - {model.name}")

except Exception as e:
    print(f"Error listing models: {e}")
    print("\nTrying alternate method with langchain_google_genai...")

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Try common model names
        test_models = [
            "gemini-pro",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "models/gemini-pro",
            "models/gemini-1.5-pro",
            "models/gemini-1.5-flash",
        ]

        print("\nTesting model availability:\n")
        for model_name in test_models:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=google_api_key,
                )
                print(f"  ✓ {model_name} - Available")
            except Exception as e:
                print(f"  ✗ {model_name} - Not available")

    except Exception as e2:
        print(f"Error testing models: {e2}")
