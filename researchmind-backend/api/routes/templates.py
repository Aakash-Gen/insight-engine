"""Research templates — pre-built starting points for common research types."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/templates", tags=["templates"])

TEMPLATES = [
    {
        "id": "competitor_analysis",
        "title": "Competitor Analysis",
        "description": "Map the competitive landscape, compare offerings, and identify market positioning.",
        "topic_template": "Competitive analysis of {company} in the {industry} industry",
        "depth": "deep",
        "example_topic": "Competitive analysis of Notion in the productivity software industry",
        "tags": ["business", "strategy"],
    },
    {
        "id": "market_research",
        "title": "Market Research",
        "description": "Understand market size, trends, key players, and growth drivers.",
        "topic_template": "Market size, trends and opportunities in the {industry} market in {year}",
        "depth": "deep",
        "example_topic": "Market size, trends and opportunities in the AI assistant market in 2025",
        "tags": ["business", "market"],
    },
    {
        "id": "technology_overview",
        "title": "Technology Deep-Dive",
        "description": "Explore how a technology works, its applications, limitations, and future trajectory.",
        "topic_template": "How {technology} works, its applications and future development",
        "depth": "standard",
        "example_topic": "How transformer neural networks work, their applications and future development",
        "tags": ["tech", "research"],
    },
    {
        "id": "literature_review",
        "title": "Literature Review",
        "description": "Survey academic and expert perspectives on a topic, synthesising key findings.",
        "topic_template": "Literature review: key research findings and debates on {topic}",
        "depth": "deep",
        "example_topic": "Literature review: key research findings and debates on intermittent fasting",
        "tags": ["academic", "research"],
    },
    {
        "id": "investment_thesis",
        "title": "Investment Thesis",
        "description": "Evaluate an investment opportunity: fundamentals, risks, growth potential.",
        "topic_template": "Investment thesis for {company_or_sector}: fundamentals, risks, and upside",
        "depth": "deep",
        "example_topic": "Investment thesis for Nvidia: fundamentals, risks, and upside",
        "tags": ["finance", "investment"],
    },
    {
        "id": "product_research",
        "title": "Product Research",
        "description": "Research product options in a category: features, pricing, and user sentiment.",
        "topic_template": "Best {product_category} in {year}: comparison, pricing, and user reviews",
        "depth": "standard",
        "example_topic": "Best project management tools in 2025: comparison, pricing, and user reviews",
        "tags": ["consumer", "product"],
    },
    {
        "id": "quick_overview",
        "title": "Quick Overview",
        "description": "Get a fast, high-level summary of any topic in minutes.",
        "topic_template": "{topic}",
        "depth": "quick",
        "example_topic": "What is retrieval-augmented generation (RAG)?",
        "tags": ["general"],
    },
]


@router.get("")
async def list_templates() -> list:
    """Return all available research templates."""
    return TEMPLATES


@router.get("/{template_id}")
async def get_template(template_id: str) -> dict:
    """Return a single template by ID."""
    for t in TEMPLATES:
        if t["id"] == template_id:
            return t
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Template not found.")
