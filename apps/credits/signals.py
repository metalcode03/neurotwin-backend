"""
Signal handlers for credit system.

Handles user creation and subscription tier changes.
Requirements: 1.2, 2.7
"""

from datetime import date
from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

from apps.subscription.models import Subscription, SubscriptionTier
from apps.credits.models import UserCredits
from apps.credits.constants import TIER_CREDIT_ALLOCATIONS


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_credits(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
    """
    Create UserCredits record when a new user is created.
    
    Initializes credits based on user's subscription tier.
    Requirements: 1.2-1.9
    
    Args:
        sender: The User model class
        instance: The User instance being saved
        created: Boolean indicating if this is a new user
        **kwargs: Additional signal arguments
    """
    if not created:
        return
    
    # Get user's subscription tier (default to FREE if not exists)
    try:
        subscription = instance.subscription
        tier = subscription.tier.upper()
    except (AttributeError, Subscription.DoesNotExist):
        tier = 'FREE'
    
    # Get monthly credit allocation for tier
    monthly_credits = TIER_CREDIT_ALLOCATIONS.get(tier, TIER_CREDIT_ALLOCATIONS['FREE'])
    
    # Create UserCredits record
    UserCredits.objects.create(
        user=instance,
        monthly_credits=monthly_credits,
        remaining_credits=monthly_credits,
        used_credits=0,
        purchased_credits=0,
        last_reset_date=date.today()
    )


@receiver(post_save, sender=Subscription)
def handle_subscription_tier_change(sender: Any, instance: Subscription, created: bool, **kwargs: Any) -> None:
    """
    Handle subscription tier changes and update user credits.
    
    On tier upgrade: Update monthly_credits and add difference to remaining_credits
    On tier downgrade: Update monthly_credits but preserve remaining_credits
    
    Requirements: 2.7
    
    Args:
        sender: The Subscription model class
        instance: The Subscription instance being saved
        created: Boolean indicating if this is a new subscription
        **kwargs: Additional signal arguments
    """
    # Skip if this is a new subscription (handled by user creation signal)
    if created:
        return
    
    # Get or create UserCredits for this user
    user_credits, credits_created = UserCredits.objects.get_or_create(
        user=instance.user,
        defaults={
            'monthly_credits': TIER_CREDIT_ALLOCATIONS['FREE'],
            'remaining_credits': TIER_CREDIT_ALLOCATIONS['FREE'],
            'used_credits': 0,
            'purchased_credits': 0,
            'last_reset_date': date.today()
        }
    )
    
    # If credits were just created, no need to update
    if credits_created:
        return
    
    # Get new tier allocation
    new_tier = instance.tier.upper()
    new_monthly_credits = TIER_CREDIT_ALLOCATIONS.get(new_tier, TIER_CREDIT_ALLOCATIONS['FREE'])
    
    # Calculate the difference
    old_monthly_credits = user_credits.monthly_credits
    credit_difference = new_monthly_credits - old_monthly_credits
    
    # Update monthly_credits
    user_credits.monthly_credits = new_monthly_credits
    
    # On upgrade (positive difference), add to remaining_credits
    # On downgrade (negative difference), preserve remaining_credits
    if credit_difference > 0:
        user_credits.remaining_credits += credit_difference
    
    user_credits.save()
