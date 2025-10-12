"""
Flask CLI commands for administrative tasks
"""
import click
from flask.cli import with_appcontext
from app import db
from app.models import User
from app.services.credit_service import CreditService


@click.command('add-credits')
@click.argument('user_id', type=int)
@click.argument('amount', type=int)
@click.option('--description', '-d', default='Manual credit adjustment', help='Description for the credit transaction')
@with_appcontext
def add_credits_command(user_id, amount, description):
    """
    Add credits to a specific user.

    Usage:
        flask add-credits USER_ID AMOUNT [--description "Custom description"]

    Examples:
        flask add-credits 3 1000
        flask add-credits 3 1000 --description "Promotional credits"
        railway run flask add-credits 3 1000
    """
    try:
        # Get the user
        user = User.query.get(user_id)
        if not user:
            click.echo(click.style(f'Error: User with ID {user_id} not found', fg='red'))
            return

        # Validate amount
        if amount <= 0:
            click.echo(click.style(f'Error: Amount must be positive (got {amount})', fg='red'))
            return

        # Add credits
        credit_service = CreditService()
        credit_service.add_credits(
            user_id=user_id,
            amount=amount,
            description=description
        )

        # Show success message
        click.echo(click.style('✓ Credits added successfully!', fg='green'))
        click.echo(f'  User: {user.email} (ID: {user_id})')
        click.echo(f'  Amount: +{amount:,} credits')
        click.echo(f'  New Balance: {user.credit_balance:,} credits')
        click.echo(f'  Description: {description}')

    except Exception as e:
        click.echo(click.style(f'Error: {str(e)}', fg='red'))
        db.session.rollback()


@click.command('deduct-credits')
@click.argument('user_id', type=int)
@click.argument('amount', type=int)
@click.option('--description', '-d', default='Manual credit deduction', help='Description for the credit transaction')
@with_appcontext
def deduct_credits_command(user_id, amount, description):
    """
    Deduct credits from a specific user.

    Usage:
        flask deduct-credits USER_ID AMOUNT [--description "Custom description"]

    Examples:
        flask deduct-credits 3 500
        flask deduct-credits 3 500 --description "Credit adjustment"
    """
    try:
        # Get the user
        user = User.query.get(user_id)
        if not user:
            click.echo(click.style(f'Error: User with ID {user_id} not found', fg='red'))
            return

        # Validate amount
        if amount <= 0:
            click.echo(click.style(f'Error: Amount must be positive (got {amount})', fg='red'))
            return

        # Check if user has enough credits
        if user.credit_balance < amount:
            click.echo(click.style(f'Warning: User only has {user.credit_balance:,} credits, but trying to deduct {amount:,}', fg='yellow'))
            if not click.confirm('Continue anyway (balance will go negative)?'):
                click.echo('Cancelled.')
                return

        # Deduct credits
        credit_service = CreditService()
        credit_service.deduct_credits(
            user_id=user_id,
            amount=amount,
            description=description
        )

        # Show success message
        click.echo(click.style('✓ Credits deducted successfully!', fg='green'))
        click.echo(f'  User: {user.email} (ID: {user_id})')
        click.echo(f'  Amount: -{amount:,} credits')
        click.echo(f'  New Balance: {user.credit_balance:,} credits')
        click.echo(f'  Description: {description}')

    except Exception as e:
        click.echo(click.style(f'Error: {str(e)}', fg='red'))
        db.session.rollback()


@click.command('show-user-credits')
@click.argument('user_id', type=int)
@with_appcontext
def show_user_credits_command(user_id):
    """
    Display credit information for a specific user.

    Usage:
        flask show-user-credits USER_ID

    Example:
        flask show-user-credits 3
    """
    try:
        # Get the user
        user = User.query.get(user_id)
        if not user:
            click.echo(click.style(f'Error: User with ID {user_id} not found', fg='red'))
            return

        # Get credit service
        credit_service = CreditService()
        balance = credit_service.get_balance(user_id)

        # Display user info
        click.echo(click.style('\nUser Credit Information', fg='cyan', bold=True))
        click.echo('=' * 50)
        click.echo(f'  User ID: {user_id}')
        click.echo(f'  Email: {user.email}')
        click.echo(f'  Current Balance: {balance:,} credits')
        click.echo(f'  Account Created: {user.created_at.strftime("%Y-%m-%d %H:%M:%S")}')
        click.echo('=' * 50)

    except Exception as e:
        click.echo(click.style(f'Error: {str(e)}', fg='red'))


def register_commands(app):
    """Register all CLI commands with the Flask app"""
    app.cli.add_command(add_credits_command)
    app.cli.add_command(deduct_credits_command)
    app.cli.add_command(show_user_credits_command)
