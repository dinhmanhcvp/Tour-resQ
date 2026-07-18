import os, sys, base64, asyncio, json
from dotenv import load_dotenv
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', '.env'))
from app.config import settings
print("API KEY:", settings.gemini_key[:5] if settings.gemini_key else None)
from app.engine.price_checker import check_price_from_image

async def test_all():
    files = os.listdir('test')
    for f in files:
        if not f.endswith('.jpg'): continue
        print(f'\n--- Testing {f} ---')
        try:
            data = base64.b64encode(open(os.path.join('test', f), 'rb').read()).decode()
            res = await check_price_from_image(data)
            if res:
                print('Verdict:', res.overall_verdict)
                for item in res.items_checked:
                    print(f'- {item.get("item_name")} (x{item.get("quantity")}) : {item.get("asked_price")} -> {item.get("db_tier")}')
            else:
                print('FAILED TO PARSE')
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test_all())
