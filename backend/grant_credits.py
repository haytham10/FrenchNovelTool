#!/usr/bin/env python3
"""
Grant or deduct credits for a user (admin script).

Usage (run from the repository or from the `backend/` folder):
  # from backend/ folder
  python grant_credits.py 3 100 --desc "Support grant" --yes

This script uses the existing application context and calls
`CreditService.admin_adjustment` so all ledger entries are recorded
and balances are computed consistently.
"""
import argparse
from datetime import datetime

from app import create_app
from app.services.credit_service import CreditService
from app.models import User


def parse_args():
    p = argparse.ArgumentParser(description='Grant or deduct credits to a user (admin)')
    p.add_argument('user_id', type=int, help='Target user id')
    p.add_argument('amount', type=int, help='Number of credits to add (positive) or deduct (negative)')
    p.add_argument('--desc', type=str, default=None, help='Description for ledger entry')
    p.add_argument('--month', type=str, default=None, help='Month YYYY-MM to assign the entry to (defaults to current month)')
    p.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    return p.parse_args()


def main():
    args = parse_args()

    app = create_app()

    with app.app_context():
        user = User.query.get(args.user_id)
        if not user:
            print(f'User id={args.user_id} not found')
            return

        month = args.month
        before = CreditService.get_credit_summary(args.user_id, month=month)
        print('Current summary:', before)

        action = 'grant' if args.amount > 0 else 'deduct'
        if not args.yes:
            confirm = input(f"About to {action} {args.amount} credits for user {user.email} (id={user.id}). Continue? [y/N]: ")
            if confirm.strip().lower() != 'y':
                print('Aborted')
                return

        description = args.desc or f'Admin adjustment ({datetime.utcnow().isoformat()}Z)'

        entry = CreditService.admin_adjustment(
            user_id=args.user_id,
            amount=args.amount,
            description=description,
            month=month
        )

        if entry is None:
            print('No ledger entry created (amount may be zero).')
            return

        print('Created ledger entry:')
        print(entry.to_dict())

        after = CreditService.get_credit_summary(args.user_id, month=month)
        print('New summary:', after)


if __name__ == '__main__':
    main()
