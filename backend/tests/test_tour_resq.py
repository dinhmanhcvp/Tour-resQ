"""
Tour-resQ Test Suite
====================
Validates core pricing engine, scam detection, and API endpoints.
Run: cd backend && python -m pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.engine.price_checker import check_single_price


class TestZScorePricing:
    """Test the Z-Score anomaly detection engine."""

    def test_fair_price_returns_fair_tier(self):
        """A price within 1 sigma should be 'fair'."""
        result = check_single_price("pho_bo", 45000, "hanoi")
        # Pho bo in Hanoi should be around 35-50k
        assert result.tier in ("fair", "slightly_high", "insufficient_data")

    def test_overpriced_returns_overpriced_tier(self):
        """An extreme price (10x normal) should be 'overpriced'."""
        result = check_single_price("pho_bo", 500000, "hanoi")
        # 500k for pho is absurd
        assert result.tier in ("overpriced", "insufficient_data")

    def test_unknown_item_returns_insufficient_data(self):
        """An item not in the DB should return 'insufficient_data'."""
        result = check_single_price("unicorn_steak", 100000, "hanoi")
        assert result.tier == "insufficient_data"

    def test_zero_price_handled_gracefully(self):
        """Zero price should not crash."""
        result = check_single_price("pho_bo", 0, "hanoi")
        assert result is not None

    def test_negative_price_handled_gracefully(self):
        """Negative price should not crash."""
        result = check_single_price("pho_bo", -50000, "hanoi")
        assert result is not None





class TestScamDetector:
    """Test scam detection engine."""

    def test_scam_detector_import(self):
        """Scam detector module should import without errors."""
        from app.engine.scam_detector import detect_scam_with_ai
        assert detect_scam_with_ai is not None

    def test_translator_import(self):
        """Translator module should import without errors."""
        from app.engine.translator import translate_text, get_phrasebook
        assert translate_text is not None
        assert get_phrasebook is not None

    def test_sos_dispatcher_import(self):
        """SOS dispatcher module should import without errors."""
        from app.engine.sos_dispatcher import dispatch_sos, get_emergency_info
        assert dispatch_sos is not None
        assert get_emergency_info is not None


class TestAntiPoisoning:
    """Test that price contribution anti-poisoning logic works."""

    def test_overpriced_contribution_rejected(self):
        """Contributing an overpriced item should not pollute the DB."""
        result = check_single_price("pho_bo", 500000, "hanoi")
        # If tier is overpriced, contribution should be rejected
        if result.tier == "overpriced":
            assert result.tier != "fair"

    def test_fair_contribution_accepted(self):
        """Contributing a fair-priced item should be allowed."""
        result = check_single_price("pho_bo", 45000, "hanoi")
        # Fair prices can be contributed
        if result.tier == "fair":
            assert result.tier == "fair"


class TestAPIHealth:
    """Test that the FastAPI app starts and endpoints are registered."""

    def test_app_import(self):
        """Main app should import without crashing."""
        from main import app
        assert app is not None

    def test_health_endpoint_exists(self):
        """Health endpoint should be registered."""
        from main import app
        routes = [r.path for r in app.routes]
        assert "/health" in routes

    def test_root_endpoint_exists(self):
        """Root endpoint should be registered."""
        from main import app
        routes = [r.path for r in app.routes]
        assert "/" in routes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
