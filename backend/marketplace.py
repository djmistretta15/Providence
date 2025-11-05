"""Marketplace matching engine - connect buyers and sellers."""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from models import Dataset, User, UserRole
import os


class MarketplaceEngine:
    """Match buyers with relevant datasets."""

    def __init__(self, db: Session):
        """Initialize marketplace engine."""
        self.db = db
        self.commission_rate = float(os.getenv("COMMISSION_RATE", "0.12"))

    def find_matching_datasets(
        self,
        buyer: User,
        categories: Optional[List[str]] = None,
        min_records: int = 0,
        max_price: Optional[float] = None,
        min_confidence: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Find datasets matching buyer's criteria."""
        query = self.db.query(Dataset).filter(
            Dataset.is_for_sale == True,
            Dataset.owner_id != buyer.id  # Don't show buyer's own datasets
        )

        # Filter by confidence score
        if min_confidence:
            query = query.filter(Dataset.confidence_score >= min_confidence)

        # Filter by record count
        if min_records:
            query = query.filter(Dataset.total_records >= min_records)

        # Filter by price
        if max_price:
            query = query.filter(Dataset.price <= max_price)

        datasets = query.all()

        # Calculate match scores
        scored_datasets = []
        for dataset in datasets:
            score = self._calculate_match_score(buyer, dataset, categories)
            if score > 0:
                scored_datasets.append({
                    "dataset": dataset,
                    "match_score": score
                })

        # Sort by match score
        scored_datasets.sort(key=lambda x: x["match_score"], reverse=True)

        return scored_datasets

    def _calculate_match_score(
        self,
        buyer: User,
        dataset: Dataset,
        requested_categories: Optional[List[str]] = None
    ) -> float:
        """Calculate match score between buyer and dataset (0-1)."""
        score = 0.0

        # Base score: data quality
        if dataset.confidence_score:
            score += dataset.confidence_score * 0.3

        # Category matching
        if requested_categories and dataset.data_categories:
            matching_categories = set(requested_categories) & set(dataset.data_categories)
            category_score = len(matching_categories) / len(requested_categories)
            score += category_score * 0.4

        # Research interest matching
        if buyer.research_interests and dataset.description:
            interest_keywords = buyer.research_interests.lower().split()
            description_lower = dataset.description.lower()
            matching_keywords = sum(1 for keyword in interest_keywords if keyword in description_lower)
            interest_score = min(matching_keywords / len(interest_keywords), 1.0) if interest_keywords else 0
            score += interest_score * 0.2

        # Record count (more is better)
        if dataset.total_records:
            record_score = min(dataset.total_records / 10000, 1.0)  # Normalize to 10k records
            score += record_score * 0.1

        return min(score, 1.0)

    def recommend_datasets(self, buyer: User, limit: int = 10) -> List[Dataset]:
        """Recommend datasets based on buyer's history and interests."""
        # Parse research interests
        categories = None
        if buyer.research_interests:
            # Extract potential categories from research interests
            interest_words = buyer.research_interests.lower().split()
            common_categories = ["vitals", "labs", "medications", "diagnoses", "procedures"]
            categories = [cat for cat in common_categories if cat in interest_words]

        # Find matching datasets
        matches = self.find_matching_datasets(
            buyer=buyer,
            categories=categories if categories else None
        )

        # Return top matches
        return [match["dataset"] for match in matches[:limit]]

    def calculate_transaction_fees(self, sale_price: float) -> Dict[str, float]:
        """Calculate transaction fees."""
        commission = sale_price * self.commission_rate
        seller_payout = sale_price - commission

        return {
            "sale_price": sale_price,
            "commission": commission,
            "commission_rate": self.commission_rate,
            "seller_payout": seller_payout
        }

    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get marketplace statistics."""
        total_listings = self.db.query(Dataset).filter(
            Dataset.is_for_sale == True
        ).count()

        avg_price = self.db.query(Dataset).filter(
            Dataset.is_for_sale == True,
            Dataset.price != None
        ).all()

        avg_price_value = sum(d.price for d in avg_price) / len(avg_price) if avg_price else 0

        total_records = sum(d.total_records or 0 for d in avg_price)

        return {
            "total_listings": total_listings,
            "average_price": avg_price_value,
            "total_records_available": total_records,
            "commission_rate": self.commission_rate
        }

    def validate_purchase(self, buyer: User, dataset: Dataset) -> Dict[str, Any]:
        """Validate if a purchase can proceed."""
        errors = []

        # Check if dataset is for sale
        if not dataset.is_for_sale:
            errors.append("Dataset is not for sale")

        # Check if buyer is trying to buy their own dataset
        if dataset.owner_id == buyer.id:
            errors.append("Cannot purchase your own dataset")

        # Check if dataset is properly normalized
        if dataset.status != "normalized":
            errors.append("Dataset is not ready for sale")

        # Check if price is set
        if not dataset.price or dataset.price <= 0:
            errors.append("Invalid dataset price")

        # Check if buyer has valid payment method (would check Stripe in production)
        # if not buyer.stripe_customer_id:
        #     errors.append("No payment method on file")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


def search_marketplace(
    db: Session,
    query: str,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 50
) -> List[Dataset]:
    """Search marketplace with filters."""
    search_query = db.query(Dataset).filter(
        Dataset.is_for_sale == True
    )

    # Text search
    if query:
        search_query = search_query.filter(
            (Dataset.filename.ilike(f"%{query}%")) |
            (Dataset.description.ilike(f"%{query}%"))
        )

    # Category filter
    if category:
        search_query = search_query.filter(
            Dataset.data_categories.contains([category])
        )

    # Price filters
    if min_price:
        search_query = search_query.filter(Dataset.price >= min_price)
    if max_price:
        search_query = search_query.filter(Dataset.price <= max_price)

    # Order by relevance (confidence score) and limit
    results = search_query.order_by(
        Dataset.confidence_score.desc()
    ).limit(limit).all()

    return results
