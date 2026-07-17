"""
Tour-resQ Dynamic Pricing Engine
================================
Two-layer approach:
  Layer 1: Database-backed Z-score anomaly detection (offline, fast)
  Layer 2: Gemini LLM contextual analysis (online, nuanced)

Uses a 3-tier verdict system:
  - fair: z-score <= 1.0
  - slightly_high: 1.0 < z-score <= 2.0
  - overpriced: z-score > 2.0
  - insufficient_data: sample_count < MIN_SAMPLE_SIZE

Does not make binary "Scam" decisions, but rather provides nuanced Tiers.
"""
import json
import math
from typing import Optional, Tuple
from pydantic import BaseModel, Field
import google.generativeai as genai
from app.core.config import settings
from app.data.price_db import get_price_stats

# ─────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────

class PriceEstimationData(BaseModel):
    """Structured output expected from Gemini"""
    item_name: str = Field(description="The core item being purchased, translated to English")
    quantity: float = Field(description="The number of items. If not specified, default to 1.0")
    total_asked_price_vnd: float = Field(description="The total price demanded in VND. Convert from 'k' (400k = 400000).")
    min_fair_unit_price_vnd: float = Field(description="The absolute lowest fair market price for ONE item in this specific hyper-local area.")
    max_fair_unit_price_vnd: float = Field(description="The highest acceptable fair market price for ONE item in this specific hyper-local area before it becomes a 'Tourist Premium'.")
    is_bespoke_art: bool = Field(description="True ONLY if the item is custom-made, fine art, handcrafted jewelry, or bespoke tailoring where price varies wildly by artisan skill. False for mass-produced food, transport, or standard goods.")
    typology_match: str = Field(description="If this matches a known scam pattern (e.g. 'Street Vendor Overcharge', 'Taxi Meter Jump'), output the name. Otherwise 'None'.")

class PriceAssessmentResult(BaseModel):
    item_name: str
    unit_price: float
    max_fair_price: float
    markup_percentage: float
    tier: str  # FAIR, PREMIUM, EXTREME_OVERCHARGE, BESPOKE_ART
    assessment_message: str
    typology_match: str

class PriceCheckResult(BaseModel):
    """Result from the DB-backed price check (Layer 1)."""
    item_name: str
    asked_price: float
    mean_price: float
    std_dev: float
    z_score: float
    sample_count: int
    tier: str  # fair, slightly_high, overpriced, insufficient_data
    confidence: float  # 0.0 - 1.0
    price_range: str  # e.g. "35,000 - 65,000 VND"
    message: str
    source: str = "database"
    last_updated: str = ""


# ─────────────────────────────────────────────────────────
# LAYER 1: DATABASE-BACKED PRICE CHECK (offline, fast)
# ─────────────────────────────────────────────────────────

def check_single_price(
    item_name: str,
    asked_price: float,
    region: str = "hanoi",
    venue_type: str = "all",
) -> PriceCheckResult:
    """
    Check a single item price against the SQLite price database.
    Uses Z-score anomaly detection with configurable thresholds.
    
    Returns insufficient_data when sample_count < MIN_SAMPLE_SIZE.
    """
    stats = get_price_stats(region, item_name, venue_type)
    
    if stats is None:
        return PriceCheckResult(
            item_name=item_name,
            asked_price=asked_price,
            mean_price=0,
            std_dev=0,
            z_score=0,
            sample_count=0,
            tier="insufficient_data",
            confidence=0.0,
            price_range="N/A",
            message=f"No price data found for '{item_name}' in {region}. Cannot verify.",
        )
    
    sample_count = stats["sample_count"]
    mean_price = stats["mean_price"]
    std_dev = stats["std_dev"]
    min_price = stats["min_price"]
    max_price = stats["max_price"]
    last_updated = stats.get("last_updated", "")
    
    # Refuse to conclude if insufficient data
    if sample_count < settings.MIN_SAMPLE_SIZE:
        return PriceCheckResult(
            item_name=item_name,
            asked_price=asked_price,
            mean_price=mean_price,
            std_dev=std_dev,
            z_score=0,
            sample_count=sample_count,
            tier="insufficient_data",
            confidence=sample_count / settings.MIN_SAMPLE_SIZE,
            price_range=f"{int(min_price):,} - {int(max_price):,} VND",
            message=f"Only {sample_count} price samples for '{item_name}' in {region}. "
                    f"Need at least {settings.MIN_SAMPLE_SIZE} to make a reliable verdict. "
                    f"Current range: {int(min_price):,} - {int(max_price):,} VND.",
            last_updated=last_updated,
        )
    
    # Calculate Z-score
    if std_dev > 0:
        z_score = (asked_price - mean_price) / std_dev
    else:
        # All samples are identical — any deviation is significant
        z_score = 0.0 if asked_price == mean_price else 3.0
    
    # Determine tier based on z-score thresholds from config
    if z_score <= settings.PRICE_TIER_GREEN:
        tier = "fair"
        message = (f"Fair price. {int(asked_price):,} VND is within the normal range "
                   f"for {item_name} in {region} (avg: {int(mean_price):,} VND).")
    elif z_score <= settings.PRICE_TIER_YELLOW:
        tier = "slightly_high"
        message = (f"Slightly above average. {int(asked_price):,} VND is higher than "
                   f"the mean of {int(mean_price):,} VND but may be normal for this venue type.")
    else:
        tier = "overpriced"
        message = (f"Significantly overpriced. {int(asked_price):,} VND is {z_score:.1f} "
                   f"standard deviations above the mean of {int(mean_price):,} VND. "
                   f"Normal range: {int(min_price):,} - {int(max_price):,} VND.")
    
    # Confidence based on sample count (more data = higher confidence)
    confidence = min(1.0, sample_count / 20)  # 20+ samples = 100% confidence
    
    return PriceCheckResult(
        item_name=item_name,
        asked_price=asked_price,
        mean_price=mean_price,
        std_dev=std_dev,
        z_score=round(z_score, 2),
        sample_count=sample_count,
        tier=tier,
        confidence=round(confidence, 2),
        price_range=f"{int(min_price):,} - {int(max_price):,} VND",
        message=message,
        last_updated=last_updated,
    )

def calculate_tier_and_message(
    unit_price: float, 
    max_fair: float, 
    is_bespoke: bool, 
    lang: str = "en"
) -> Tuple[str, float, str]:
    """Calculates the markup percentage and assigns a nuanced tier."""
    
    if max_fair <= 0:
        return "UNKNOWN", 0.0, "Could not determine a fair baseline price."

    markup = ((unit_price - max_fair) / max_fair) * 100
    
    # Handle bespoke items first
    if is_bespoke:
        msg = "This is a bespoke, handmade, or artistic item. Pricing depends heavily on craftsmanship and material quality. Inspect carefully before negotiating."
        if lang == "vi":
            msg = "Đây là sản phẩm thủ công/đặc thù. Giá trị phụ thuộc vào độ tinh xảo và chất liệu. Hãy kiểm tra kỹ trước khi chốt giá."
        return "BESPOKE_ART", markup, msg

    # Calculate tiers based on markup
    if markup <= 20:
        msg = f"Fair price. This is within the normal market range for this area."
        if lang == "vi":
            msg = "Giá hợp lý. Mức giá này nằm trong mặt bằng chung tại khu vực này."
        return "FAIR", markup, msg
        
    elif markup <= 100:
        msg = f"Tourist Premium. You are paying a {(markup):.0f}% markup above average. You should negotiate down to around {int(max_fair):,} VND."
        if lang == "vi":
            msg = f"Giá khách du lịch. Bạn đang bị tính chênh {markup:.0f}%. Khuyên bạn nên mặc cả xuống khoảng {int(max_fair):,} VNĐ."
        return "PREMIUM", markup, msg
        
    else:
        msg = f"Severe Overcharge! This is a {(markup):.0f}% markup. The real price should be around {int(max_fair):,} VND. Strongly recommend refusing or walking away."
        if lang == "vi":
            msg = f"Dấu hiệu chém giá nghiêm trọng! Mức giá bị dội lên {markup:.0f}% (giá gốc chỉ khoảng {int(max_fair):,} VNĐ). Tuyệt đối không mua hoặc trả đúng giá."
        return "EXTREME_OVERCHARGE", markup, msg

async def analyze_price_context(
    description: str,
    location_context: str,
    lang: str = "en"
) -> Optional[PriceAssessmentResult]:
    """
    Advanced LLM query to extract entities and estimate local fair value.
    """
    if not settings.gemini_key:
        return None

    genai.configure(api_key=settings.gemini_key)
    # Using Gemini 1.5 Pro or Flash to support response_schema
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""You are a hyper-local pricing expert in Vietnam.
Analyze the following tourist interaction: "{description}"
Context/Location: {location_context}

IMPORTANT SLANG DICTIONARY & CONTEXT RULES:
- "lít" = 100,000 VND, "củ" = 1,000,000 VND
- THREATS: If the interaction involves intimidation (e.g., "không đưa đủ không xong đâu"), set typology_match to "Intimidation / Slang Overcharge".
- ROUTE DEVIATION: If the user says the taxi is "đi ngược hướng" (going the wrong way) or "nhảy nhanh" (meter tampering), set typology_match to "KIDNAPPING_RISK". This is an extreme emergency.
- WEATHER SURGE: If the context mentions "mưa" (rain), "ngập" (flooding), or rush hour, increase the `max_fair_unit_price_vnd` by 80% to account for legitimate surge pricing. Do not flag as an overcharge if it's within this surge bracket.

Extract the item, quantity, and total demanded price.
Estimate the min and max FAIR market price for ONE UNIT of this item in this SPECIFIC location.
If it's a bespoke/handicraft item, set is_bespoke_art to true.
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=PriceEstimationData,
                temperature=0.1
            )
        )
        
        if not response.text:
            return None
            
        data_dict = json.loads(response.text)
        data = PriceEstimationData(**data_dict)
        
        # Calculate derived metrics
        qty = data.quantity if data.quantity > 0 else 1.0
        unit_price = data.total_asked_price_vnd / qty
        
        tier, markup, msg = calculate_tier_and_message(
            unit_price=unit_price,
            max_fair=data.max_fair_unit_price_vnd,
            is_bespoke=data.is_bespoke_art,
            lang=lang
        )
        
        return PriceAssessmentResult(
            item_name=data.item_name,
            unit_price=unit_price,
            max_fair_price=data.max_fair_unit_price_vnd,
            markup_percentage=markup,
            tier=tier,
            assessment_message=msg,
            typology_match=data.typology_match
        )
        
    except Exception as e:
        print(f"Price Analysis Error: {e}")
        return None
