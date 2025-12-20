import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GOOGLE_API_KEY")
if key:
    print(f"GOOGLE_API_KEY found! Length: {len(key)}")
    print(f"Key start: {key[:4]}...")
else:
    print("GOOGLE_API_KEY NOT found.")
