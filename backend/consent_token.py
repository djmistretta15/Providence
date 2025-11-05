"""Blockchain-ready consent token system."""
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from models import Dataset, User, AuditLog


class ConsentToken:
    """Blockchain-ready consent token with cryptographic hash chain."""

    def __init__(self, user_id: int, dataset_id: int, consent_text: str):
        """Initialize consent token."""
        self.user_id = user_id
        self.dataset_id = dataset_id
        self.consent_text = consent_text
        self.timestamp = datetime.utcnow()
        self.version = "1.0"

    def generate_token(self, previous_hash: Optional[str] = None) -> str:
        """Generate cryptographic hash token."""
        token_data = {
            "version": self.version,
            "user_id": self.user_id,
            "dataset_id": self.dataset_id,
            "consent_text": self.consent_text,
            "timestamp": self.timestamp.isoformat(),
            "previous_hash": previous_hash or "genesis"
        }

        # Create deterministic JSON string
        token_string = json.dumps(token_data, sort_keys=True)

        # Generate SHA-256 hash
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()

        return token_hash

    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary."""
        return {
            "user_id": self.user_id,
            "dataset_id": self.dataset_id,
            "consent_text": self.consent_text,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version
        }


class ConsentChain:
    """Consent token chain for audit trail."""

    def __init__(self, db: Session):
        """Initialize consent chain."""
        self.db = db
        self.chain: List[ConsentToken] = []

    def add_consent(self, user_id: int, dataset_id: int, consent_text: str) -> str:
        """Add new consent to chain."""
        # Get previous hash
        previous_hash = None
        if self.chain:
            previous_hash = self.chain[-1].generate_token()

        # Create new token
        token = ConsentToken(user_id, dataset_id, consent_text)
        token_hash = token.generate_token(previous_hash)

        # Add to chain
        self.chain.append(token)

        # Store in audit log
        audit_entry = AuditLog(
            user_id=user_id,
            event_type="consent_token_created",
            resource_type="dataset",
            resource_id=dataset_id,
            details={
                "token_hash": token_hash,
                "previous_hash": previous_hash,
                "consent_text": consent_text
            },
            success=True
        )
        self.db.add(audit_entry)
        self.db.commit()

        return token_hash

    def verify_chain(self) -> bool:
        """Verify integrity of consent chain."""
        if not self.chain:
            return True

        for i in range(1, len(self.chain)):
            current_token = self.chain[i]
            previous_token = self.chain[i - 1]

            # Recalculate hash with previous hash
            previous_hash = previous_token.generate_token()
            expected_hash = current_token.generate_token(previous_hash)

            # Verify hash matches
            actual_hash = current_token.generate_token(previous_hash)
            if expected_hash != actual_hash:
                return False

        return True

    def get_consent_history(self, dataset_id: int) -> List[Dict[str, Any]]:
        """Get consent history for a dataset."""
        history = []
        for token in self.chain:
            if token.dataset_id == dataset_id:
                history.append(token.to_dict())

        return history


class RevenueTracking:
    """Track revenue and earnings for data sellers."""

    def __init__(self, db: Session):
        """Initialize revenue tracker."""
        self.db = db

    def record_sale(
        self,
        seller_id: int,
        buyer_id: int,
        dataset_id: int,
        sale_price: float,
        commission_rate: float = 0.12
    ) -> Dict[str, float]:
        """Record a data sale and calculate revenue split."""
        commission = sale_price * commission_rate
        seller_revenue = sale_price - commission

        # Update seller earnings
        seller = self.db.query(User).filter(User.id == seller_id).first()
        if seller:
            seller.total_earnings += seller_revenue
            self.db.commit()

        # Create audit trail
        audit = AuditLog(
            user_id=seller_id,
            event_type="revenue_recorded",
            resource_type="dataset",
            resource_id=dataset_id,
            details={
                "buyer_id": buyer_id,
                "sale_price": sale_price,
                "commission": commission,
                "seller_revenue": seller_revenue
            },
            success=True
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "sale_price": sale_price,
            "commission": commission,
            "commission_rate": commission_rate,
            "seller_revenue": seller_revenue
        }

    def get_earnings_summary(self, user_id: int) -> Dict[str, Any]:
        """Get earnings summary for a user."""
        from models import Billing

        # Get all sales
        sales = self.db.query(Billing).filter(
            Billing.user_id == user_id,
            Billing.transaction_type == "sale"
        ).all()

        # Calculate metrics
        total_sales = len(sales)
        total_revenue = sum(s.amount for s in sales)
        avg_sale_price = total_revenue / total_sales if total_sales > 0 else 0

        # Get recent sales
        recent_sales = self.db.query(Billing).filter(
            Billing.user_id == user_id,
            Billing.transaction_type == "sale"
        ).order_by(Billing.created_at.desc()).limit(10).all()

        return {
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "average_sale_price": avg_sale_price,
            "recent_sales": [
                {
                    "amount": sale.amount,
                    "dataset_id": sale.dataset_id,
                    "created_at": sale.created_at.isoformat(),
                    "buyer_id": sale.buyer_id
                }
                for sale in recent_sales
            ]
        }

    def calculate_platform_revenue(self) -> Dict[str, Any]:
        """Calculate total platform revenue from commissions."""
        from models import Billing

        commissions = self.db.query(Billing).filter(
            Billing.transaction_type == "commission"
        ).all()

        total_commission = sum(c.amount for c in commissions)
        total_transactions = len(commissions)

        return {
            "total_commission_revenue": total_commission,
            "total_transactions": total_transactions,
            "average_commission": total_commission / total_transactions if total_transactions > 0 else 0
        }


def create_consent_token_for_dataset(
    db: Session,
    user_id: int,
    dataset_id: int,
    consent_text: str
) -> str:
    """Helper function to create consent token for a dataset."""
    chain = ConsentChain(db)
    token_hash = chain.add_consent(user_id, dataset_id, consent_text)

    # Update dataset with token
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset:
        dataset.consent_token = token_hash
        db.commit()

    return token_hash


def verify_consent_token(db: Session, dataset_id: int, token_hash: str) -> bool:
    """Verify consent token for a dataset."""
    # Get dataset
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        return False

    # Check if token matches
    return dataset.consent_token == token_hash
