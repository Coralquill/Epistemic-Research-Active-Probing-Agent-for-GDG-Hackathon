"""
FastAPI Mock Benchmark Server: Simulates live web environments with stale documentation,
echo-chamber syndication, and undocumented edge-case behaviors for testing and hackathon demos.
"""

from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(
    title="Epistemic Agent Benchmark Testbed",
    description="Simulates discrepancies between static web docs and true runtime API behaviors."
)


# ============================================================================
# Scenario 1: Stale Documentation vs. Live Auth Behavior
# ============================================================================

@app.get("/docs/auth-spec")
def get_auth_docs():
    """Simulates a static documentation page that is outdated."""
    return {
        "title": "API Authentication Specification (v2.1)",
        "last_updated": "2022-04-12",
        "documentation": "To authenticate, pass your secret token in the 'X-API-Key' HTTP header."
    }


@app.get("/api/v1/secure-data")
def get_secure_data(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None)
):
    """
    Live API Endpoint:
    Returns 400 if user relies on the stale 'X-API-Key' header.
    Requires modern 'Authorization: Bearer <token>' header.
    """
    if x_api_key and not authorization:
        raise HTTPException(
            status_code=400,
            detail="DEPRECATED_AUTH_METHOD: 'X-API-Key' was deprecated in v3.0. Use 'Authorization: Bearer <token>'."
        )

    if authorization and authorization.startswith("Bearer "):
        return {
            "status": "SUCCESS",
            "message": "Authenticated successfully using Bearer token.",
            "data": [10, 20, 30, 40]
        }

    raise HTTPException(
        status_code=401,
        detail="UNAUTHORIZED: Missing valid 'Authorization: Bearer <token>' header."
    )


# ============================================================================
# Scenario 2: Undocumented Volume Pricing Edge Case
# ============================================================================

@app.get("/docs/pricing")
def get_pricing_docs():
    """Static pricing documentation."""
    return {
        "title": "Enterprise Tier Pricing",
        "tiers": [
            {"min_units": 1, "max_units": 100, "price_per_unit": 10.0},
            {"min_units": 101, "max_units": 1000, "price_per_unit": 8.0}
        ],
        "notes": "Contact sales for orders above 1,000 units."
    }


class PricingRequest(BaseModel):
    units: int


@app.post("/api/v1/pricing/calculate")
def calculate_live_price(req: PricingRequest):
    """
    Live Pricing Engine:
    Implements an unannounced dynamic 50% discount for orders above 2,500 units.
    """
    units = req.units
    if units <= 0:
        raise HTTPException(status_code=400, detail="Units must be positive.")

    if units <= 100:
        unit_price = 10.0
    elif units <= 1000:
        unit_price = 8.0
    elif units <= 2500:
        unit_price = 6.5
    else:
        # Undocumented hidden algorithmic tier
        unit_price = 4.0

    total = units * unit_price
    return {
        "units": units,
        "effective_unit_price": unit_price,
        "total_cost": total,
        "tier_applied": "ALGORITHMIC_MEGA_VOLUME" if units > 2500 else "STANDARD"
    }


# ============================================================================
# Scenario 3: Syndicated Echo Chamber Scraper Endpoints
# ============================================================================

MOCK_SCRAPED_POSTS = {
    "blog_root": {
        "domain": "original-dev-blog.org",
        "published": "2024-01-01",
        "text": "SQLite 3.35.0 introduced the RETURNING clause, but ON CONFLICT RETURNING requires SQLite 3.38.0+."
    },
    "scraper_1": {
        "domain": "dev-aggregates-daily.com",
        "published": "2024-01-05",
        "text": "Top tech tips: SQLite 3.35.0 supports RETURNING everywhere without issues.",
        "copies": "blog_root"
    },
    "scraper_2": {
        "domain": "ai-code-hints.net",
        "published": "2024-01-08",
        "text": "Top tech tips: SQLite 3.35.0 supports RETURNING everywhere without issues.",
        "copies": "scraper_1"
    }
}


@app.get("/mock-web/posts/{post_id}")
def get_mock_post(post_id: str):
    if post_id in MOCK_SCRAPED_POSTS:
        return MOCK_SCRAPED_POSTS[post_id]
    raise HTTPException(status_code=404, detail="Post not found.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
