"""Service for managing user credits and ledger operations"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from app import db
from app.models import CreditLedger, User
from app.constants import (
    CREDIT_REASON_MONTHLY_GRANT,
    CREDIT_REASON_JOB_RESERVE,
    CREDIT_REASON_JOB_FINAL,
    CREDIT_REASON_JOB_REFUND,
    CREDIT_REASON_ADMIN_ADJUSTMENT,
    CREDIT_REASON_COVERAGE_RUN,
    MONTHLY_CREDIT_GRANT,
    PRICING_VERSION,
    CREDIT_OVERDRAFT_LIMIT,
)


class CreditService:
    """Service for credit ledger operations with race condition protection"""

    @staticmethod
    def get_current_month() -> str:
        """Get current month in YYYY-MM format"""
        return datetime.now(timezone.utc).strftime("%Y-%m")

    @staticmethod
    def get_next_reset_date() -> str:
        """Get the next credit reset date (first day of next month)"""
        now = datetime.now(timezone.utc)
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1)
        else:
            next_month = datetime(now.year, now.month + 1, 1)
        return next_month.isoformat() + "Z"

    @staticmethod
    def calculate_balance(user_id: int, month: Optional[str] = None) -> int:
        """
        Calculate credit balance for a user in a specific month.
        Returns the sum of all credit deltas for the month.

        Args:
            user_id: User ID
            month: Month in YYYY-MM format (defaults to current month)

        Returns:
            Credit balance (can be negative)
        """
        if month is None:
            month = CreditService.get_current_month()

        result = (
            db.session.query(func.coalesce(func.sum(CreditLedger.delta_credits), 0))
            .filter(CreditLedger.user_id == user_id, CreditLedger.month == month)
            .scalar()
        )

        return int(result)

    @staticmethod
    def grant_monthly_credits(
        user_id: int, month: Optional[str] = None, amount: Optional[int] = None
    ) -> CreditLedger:
        """
        Grant monthly credits to a user.

        Args:
            user_id: User ID
            month: Month in YYYY-MM format (defaults to current month)
            amount: Amount to grant (defaults to MONTHLY_CREDIT_GRANT)

        Returns:
            CreditLedger entry
        """
        if month is None:
            month = CreditService.get_current_month()
        if amount is None:
            amount = MONTHLY_CREDIT_GRANT

        # Check if grant already exists for this month
        existing = CreditLedger.query.filter_by(
            user_id=user_id, month=month, reason=CREDIT_REASON_MONTHLY_GRANT
        ).first()

        if existing:
            return existing

        entry = CreditLedger(
            user_id=user_id,
            month=month,
            delta_credits=amount,
            reason=CREDIT_REASON_MONTHLY_GRANT,
            pricing_version=PRICING_VERSION,
            description=f"Monthly credit grant for {month}",
        )
        db.session.add(entry)
        db.session.commit()

        return entry

    @staticmethod
    def ensure_monthly_grant(user_id: int) -> bool:
        """
        Ensure user has received their monthly grant for the current month.
        Called on first login or job submission each month.

        Args:
            user_id: User ID

        Returns:
            True if grant was created, False if it already existed
        """
        month = CreditService.get_current_month()

        # Check if grant exists
        existing = CreditLedger.query.filter_by(
            user_id=user_id, month=month, reason=CREDIT_REASON_MONTHLY_GRANT
        ).first()

        if not existing:
            CreditService.grant_monthly_credits(user_id, month)
            return True

        return False

    @staticmethod
    def reserve_credits(
        user_id: int, job_id: int, amount: int, description: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Reserve (consume) credits for a job (soft reservation).
        Uses database-level locking to prevent race conditions.

        Args:
            user_id: User ID
            job_id: Job ID
            amount: Amount to reserve (positive number, will be stored as negative)
            description: Optional description

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        month = CreditService.get_current_month()

        # Ensure monthly grant exists
        CreditService.ensure_monthly_grant(user_id)

        # Use SELECT FOR UPDATE to lock the user's ledger entries for this month
        # This prevents race conditions when multiple requests try to reserve credits
        try:
            # Lock all ledger rows for this user/month, then sum in Python
            rows = (
                db.session.query(CreditLedger.delta_credits)
                .filter(CreditLedger.user_id == user_id, CreditLedger.month == month)
                .with_for_update()
                .all()
            )
            current_balance = sum(row[0] for row in rows) if rows else 0
            new_balance = current_balance - amount

            # Check if balance would go below overdraft limit
            if new_balance < CREDIT_OVERDRAFT_LIMIT:
                db.session.rollback()
                return (
                    False,
                    f"Insufficient credits. Current: {current_balance}, Required: {amount}, Overdraft limit: {CREDIT_OVERDRAFT_LIMIT}",
                )

            # Create reservation entry
            entry = CreditLedger(
                user_id=user_id,
                month=month,
                delta_credits=-amount,  # Negative for consumption
                reason=CREDIT_REASON_JOB_RESERVE,
                job_id=job_id,
                pricing_version=PRICING_VERSION,
                description=description or f"Reserved credits for job {job_id}",
            )
            db.session.add(entry)
            db.session.commit()

            return True, None

        except Exception as e:
            db.session.rollback()
            return False, f"Failed to reserve credits: {str(e)}"

    @staticmethod
    def adjust_final_credits(
        user_id: int,
        job_id: int,
        reserved_amount: int,
        actual_amount: int,
        description: Optional[str] = None,
    ) -> CreditLedger:
        """
        Adjust credits after job completion (difference between reserved and actual).

        Args:
            user_id: User ID
            job_id: Job ID
            reserved_amount: Amount originally reserved
            actual_amount: Actual amount used
            description: Optional description

        Returns:
            CreditLedger entry for the adjustment (or None if no adjustment needed)
        """
        month = CreditService.get_current_month()
        delta = reserved_amount - actual_amount

        # If no adjustment needed, return None
        if delta == 0:
            return None

        # Create adjustment entry (positive if actual < reserved, negative if actual > reserved)
        entry = CreditLedger(
            user_id=user_id,
            month=month,
            delta_credits=delta,
            reason=CREDIT_REASON_JOB_FINAL,
            job_id=job_id,
            pricing_version=PRICING_VERSION,
            description=description
            or f"Credit adjustment for job {job_id}: reserved {reserved_amount}, used {actual_amount}",
        )
        db.session.add(entry)
        db.session.commit()

        return entry

    @staticmethod
    def refund_credits(
        user_id: int, job_id: int, amount: int, description: Optional[str] = None
    ) -> CreditLedger:
        """
        Refund credits for a failed job.

        Args:
            user_id: User ID
            job_id: Job ID
            amount: Amount to refund (positive number)
            description: Optional description

        Returns:
            CreditLedger entry
        """
        month = CreditService.get_current_month()

        entry = CreditLedger(
            user_id=user_id,
            month=month,
            delta_credits=amount,  # Positive for refund
            reason=CREDIT_REASON_JOB_REFUND,
            job_id=job_id,
            pricing_version=PRICING_VERSION,
            description=description or f"Refund for failed job {job_id}",
        )
        db.session.add(entry)
        db.session.commit()

        return entry

    @staticmethod
    def charge_coverage_run(
        user_id: int, coverage_run_id: int, amount: int, description: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Charge credits for a coverage run.
        Uses database-level locking to prevent race conditions.

        Args:
            user_id: User ID
            coverage_run_id: Coverage run ID
            amount: Amount to charge (positive number, will be stored as negative)
            description: Optional description

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        from app.constants import CREDIT_REASON_COVERAGE_RUN, CREDIT_OVERDRAFT_LIMIT

        month = CreditService.get_current_month()

        # Ensure monthly grant exists
        CreditService.ensure_monthly_grant(user_id)

        # Use SELECT FOR UPDATE to lock the user's ledger entries for this month
        try:
            # Lock all ledger rows for this user/month, then sum in Python
            rows = (
                db.session.query(CreditLedger.delta_credits)
                .filter(CreditLedger.user_id == user_id, CreditLedger.month == month)
                .with_for_update()
                .all()
            )
            current_balance = sum(row[0] for row in rows) if rows else 0
            new_balance = current_balance - amount

            # Check if balance would go below overdraft limit
            if new_balance < CREDIT_OVERDRAFT_LIMIT:
                db.session.rollback()
                return (
                    False,
                    f"Insufficient credits. Current: {current_balance}, Required: {amount}, Overdraft limit: {CREDIT_OVERDRAFT_LIMIT}",
                )

            # Create charge entry
            entry = CreditLedger(
                user_id=user_id,
                month=month,
                delta_credits=-amount,  # Negative for consumption
                reason=CREDIT_REASON_COVERAGE_RUN,
                pricing_version=PRICING_VERSION,
                description=description or f"Coverage run #{coverage_run_id}",
            )
            db.session.add(entry)
            db.session.commit()

            return True, None

        except Exception as e:
            db.session.rollback()
            return False, f"Failed to charge credits: {str(e)}"

    @staticmethod
    def admin_adjustment(
        user_id: int, amount: int, description: str, month: Optional[str] = None
    ) -> CreditLedger:
        """
        Manual credit adjustment by admin.

        Args:
            user_id: User ID
            amount: Amount to adjust (can be positive or negative)
            description: Description of the adjustment
            month: Month in YYYY-MM format (defaults to current month)

        Returns:
            CreditLedger entry
        """
        if month is None:
            month = CreditService.get_current_month()

        entry = CreditLedger(
            user_id=user_id,
            month=month,
            delta_credits=amount,
            reason=CREDIT_REASON_ADMIN_ADJUSTMENT,
            pricing_version=PRICING_VERSION,
            description=description,
        )
        db.session.add(entry)
        db.session.commit()

        return entry

    @staticmethod
    def get_credit_summary(user_id: int, month: Optional[str] = None) -> Dict[str, Any]:
        """
        Get credit summary for a user in a specific month.

        Args:
            user_id: User ID
            month: Month in YYYY-MM format (defaults to current month)

        Returns:
            Dictionary with balance, granted, used, and next_reset
        """
        if month is None:
            month = CreditService.get_current_month()

        # Ensure monthly grant exists
        CreditService.ensure_monthly_grant(user_id)

        # Get all entries for the month
        entries = CreditLedger.query.filter_by(user_id=user_id, month=month).all()

        granted = 0
        used = 0
        refunded = 0
        adjusted = 0

        for entry in entries:
            if entry.reason == CREDIT_REASON_MONTHLY_GRANT:
                granted += entry.delta_credits
            elif entry.reason in [CREDIT_REASON_JOB_RESERVE, CREDIT_REASON_COVERAGE_RUN]:
                used += abs(entry.delta_credits)
            elif entry.reason == CREDIT_REASON_JOB_REFUND:
                refunded += entry.delta_credits
            elif entry.reason == CREDIT_REASON_JOB_FINAL:
                # Adjustments can be positive (refund) or negative (overrun)
                if entry.delta_credits > 0:
                    refunded += entry.delta_credits
                else:
                    used += abs(entry.delta_credits)
            elif entry.reason == CREDIT_REASON_ADMIN_ADJUSTMENT:
                adjusted += entry.delta_credits

        balance = granted - used + refunded + adjusted

        return {
            "balance": balance,
            "granted": granted,
            "used": used,
            "refunded": refunded,
            "adjusted": adjusted,
            "month": month,
            "next_reset": CreditService.get_next_reset_date(),
        }

    @staticmethod
    def get_ledger_entries(
        user_id: int, month: Optional[str] = None, limit: Optional[int] = None
    ) -> list[CreditLedger]:
        """
        Get ledger entries for a user.

        Args:
            user_id: User ID
            month: Month in YYYY-MM format (optional, returns all months if None)
            limit: Maximum number of entries to return

        Returns:
            List of CreditLedger entries
        """
        query = CreditLedger.query.filter_by(user_id=user_id)

        if month:
            query = query.filter_by(month=month)

        query = query.order_by(CreditLedger.timestamp.desc())

        if limit:
            query = query.limit(limit)

        return query.all()
