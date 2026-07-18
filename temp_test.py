import asyncio, os, base64
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

from google import genai
from google.genai import types
from app.core.config import settings

async def run():
    client = genai.Client(api_key=settings.gemini_key)
    with open('test/4.jpg', 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode('utf-8')
    image_data = base64.b64decode(img_b64)
    image_part = types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
    
    ocr_schema = {
        "type": "OBJECT",
        "properties": {
            "items": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "item_name": {"type": "STRING"},
                        "item_name_vi": {"type": "STRING"},
                        "price_vnd": {"type": "NUMBER"},
                        "quantity": {"type": "NUMBER"},
                        "unit": {"type": "STRING"},
                    },
                    "required": ["item_name", "price_vnd"]
                }
            },
            "currency_detected": {"type": "STRING"},
            "language_detected": {"type": "STRING"}
        },
        "required": ["items"]
    }
    print("Calling API...")
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                "Extract items and prices. Multiply price by 1000 if it's abbreviated.",
                image_part
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ocr_schema,
                temperature=0.0
            ),
        )
        print("RESULT:")
        print(response.text)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(run())
