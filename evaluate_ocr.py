import os
import glob
import json
import base64
import time
import requests
import random
import re

# Dataset path from kagglehub download
DATASET_PATH = r"sample_receipts"
API_URL = "http://localhost:8000/api/v1/check-price-ocr"

def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def call_ocr_api(base64_image):
    payload = {
        "image_base64": base64_image,
        "language": "en"
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        return response.json()
    except Exception as e:
        print(f"API Error: {e}")
        return None

def main():
    print("Tour-resQ OCR Evaluation Script")
    print(f"Dataset path: {DATASET_PATH}")
    
    if not os.path.exists(DATASET_PATH):
        print("Dataset not found. Please wait for the download to finish.")
        return

    # In MC-OCR 2021, images are usually in folders like 'mcocr_train_data/train_images'
    # And labels are in 'mcocr_train_df.csv'. We will just find all images and sample 50.
    image_files = []
    for root, dirs, files in os.walk(DATASET_PATH):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(os.path.join(root, file))
                
    if not image_files:
        print("No images found in dataset path.")
        return
        
    print(f"Found {len(image_files)} images total.")
    
    # Sample 50 images
    sample_size = min(50, len(image_files))
    sampled_images = random.sample(image_files, sample_size)
    print(f"Evaluating on {sample_size} random images...\n")
    
    success_count = 0
    total_parsed_amount = 0
    
    results = []
    
    for idx, img_path in enumerate(sampled_images):
        print(f"[{idx+1}/{sample_size}] Processing {os.path.basename(img_path)}...")
        b64 = get_base64_image(img_path)
        
        start_time = time.time()
        res = call_ocr_api(b64)
        elapsed = time.time() - start_time
        
        if res and res.get("status") == "success":
            success_count += 1
            result_data = res.get("result", {})
            total = result_data.get("total_asked", 0)
            items = result_data.get("items_checked", [])
            print(f"  -> SUCCESS! Total extracted: {total} VND | Found {len(items)} items | Time: {elapsed:.2f}s")
            
            results.append({
                "image": os.path.basename(img_path),
                "success": True,
                "total_asked": total,
                "items_count": len(items)
            })
        else:
            print(f"  -> FAILED to parse.")
            results.append({
                "image": os.path.basename(img_path),
                "success": False
            })
            
        # Avoid rate limits
        time.sleep(2)
        
    # Print summary
    robustness = (success_count / sample_size) * 100
    print("\n" + "="*40)
    print("EVALUATION SUMMARY")
    print("="*40)
    print(f"Total Images Evaluated : {sample_size}")
    print(f"Successful Parsings    : {success_count} ({robustness:.1f}%)")
    print("="*40)
    
    # Save to a summary file
    with open("eval_results_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print("Results saved to eval_results_summary.json")

if __name__ == "__main__":
    main()
