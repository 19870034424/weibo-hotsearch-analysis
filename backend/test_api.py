import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chat.qwen_client import QwenClient

print("Testing Qwen API...")
client = QwenClient()

if not client.api_key:
    print("ERROR: API Key not loaded")
    sys.exit(1)

print(f"API Key loaded: {client.api_key[:4]}****")

try:
    response = client.chat_with_context("你好", "")
    print(f"Response: {response[:50]}...")
except Exception as e:
    print(f"Error: {e}")