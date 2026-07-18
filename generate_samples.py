from PIL import Image, ImageDraw
import os

os.makedirs("sample_receipts", exist_ok=True)

def create_receipt(filename, items, total):
    img = Image.new('RGB', (400, 600), color = (255, 255, 255))
    d = ImageDraw.Draw(img)
    y = 20
    d.text((150, y), "NHA HANG NGON", fill=(0,0,0))
    y += 40
    d.text((20, y), "HOA DON THANH TOAN", fill=(0,0,0))
    y += 40
    for item in items:
        d.text((20, y), f"{item['name']} x{item['qty']}", fill=(0,0,0))
        d.text((300, y), f"{item['price']}", fill=(0,0,0))
        y += 30
    
    y += 20
    d.text((20, y), "---------------------------", fill=(0,0,0))
    y += 30
    d.text((20, y), "TONG CONG:", fill=(0,0,0))
    d.text((300, y), f"{total}", fill=(0,0,0))
    
    img.save(os.path.join("sample_receipts", filename))

create_receipt("receipt1.jpg", [{"name": "Pho Bo", "qty": 2, "price": "100000"}, {"name": "Tra Da", "qty": 2, "price": "10000"}], 110000)
create_receipt("receipt2.jpg", [{"name": "Banh Mi", "qty": 1, "price": "30000"}, {"name": "Cafe Sua", "qty": 1, "price": "25000"}], 55000)
create_receipt("receipt3.jpg", [{"name": "Com Rang", "qty": 1, "price": "50000"}], 50000)
print("Samples generated.")
