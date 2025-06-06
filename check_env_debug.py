import os
from dotenv import load_dotenv

load_dotenv()

debug_val = os.getenv('DEBUG')
print(f"DEBUG_VALUE_FROM_OS_GETENV: '{debug_val}'")

# Also, let's try to read the file directly to see the raw line
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.strip().startswith('DEBUG='):
                print(f"RAW_DEBUG_LINE_FROM_FILE: '{line.strip()}'")
                break
except Exception as e:
    print(f"Error reading .env directly: {e}")
