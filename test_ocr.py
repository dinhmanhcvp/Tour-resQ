import os, sys, base64, asyncio, json
sys.path.insert(0, os.path.abspath('backend'))
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
            print('ERROR:', e)

asyncio.run(test_all())
