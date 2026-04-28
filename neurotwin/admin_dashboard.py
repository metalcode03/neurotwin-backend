"""
Admin dashboard callback module for NeuroTwin.

Provides KPI cards and chart data for the Unfold admin dashboard.
All queries are wrapped in try/except to return fallback values on failure.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
"""

import json
from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.authentication.models import User
from apps.credits.models import AIRequestLog, CreditUsageLog
from apps.subscription.models import Subscription


def get_kpi_cards() -> list[dict]:
    """
    Return KPI card data: total users, active subscriptions,
    total credits consumed, and total AI requests.

    Each metric query is individually wrapped so a single failure
    doesn't take down the entire card row.

    Requirements: 4.1, 4.7
    """
    cards = []

    try:
        total_users = User.objects.count()
    except Exception:
        total_users = "N/A"
    cards.append({"title": "Total Users", "metric": total_users, "icon": "people"})

    try:
        active_subs = Subscription.objects.filter(is_active=True).count()
    except Exception:
        active_subs = "N/A"
    cards.append({"title": "Active Subscriptions", "metric": active_subs, "icon": "card_membership"})

    try:
        result = CreditUsageLog.objects.aggregate(total=Sum("credits_consumed"))
        total_credits = result["total"] or 0
    except Exception:
        total_credits = "N/A"
    cards.append({"title": "Credits Consumed", "metric": total_credits, "icon": "data_usage"})

    try:
        total_ai_requests = AIRequestLog.objects.count()
    except Exception:
        total_ai_requests = "N/A"
    cards.append({"title": "AI Requests", "metric": total_ai_requests, "icon": "smart_toy"})

    return cards


def get_ai_requests_chart_data() -> dict | None:
    """
    Return 30-day AI request volume as a line chart dataset.

    Requirements: 4.2, 4.7
    """
    try:
        thirty_days_ago = timezone.now() - timedelta(days=30)
        qs = (
            AIRequestLog.objects.filter(timestamp__gte=thirty_days_ago)
            .annotate(date=TruncDate("timestamp"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )
        labels = [entry["date"].strftime("%Y-%m-%d") for entry in qs]
        data = [entry["count"] for entry in qs]
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "AI Requests",
                    "data": data,
                    "borderColor": "oklch(60% .22 262)",
                    "backgroundColor": "oklch(60% .22 262 / 0.1)",
                }
            ],
        }
    except Exception:
        return None


def get_credit_consumption_chart_data() -> dict | None:
    """
    Return credit consumption grouped by brain_mode as a bar chart dataset.

    Requirements: 4.3, 4.7
    """
    try:
        qs = (
            CreditUsageLog.objects.values("brain_mode")
            .annotate(total=Sum("credits_consumed"))
            .order_by("brain_mode")
        )
        labels = [entry["brain_mode"] for entry in qs]
        data = [entry["total"] for entry in qs]
        colors = [
            "oklch(60% .22 262)",
            "oklch(70% .17 265)",
            "oklch(52% .24 260)",
        ]
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Credits Consumed",
                    "data": data,
                    "backgroundColor": colors[: len(labels)],
                }
            ],
        }
    except Exception:
        return None


def get_subscription_tier_chart_data() -> dict | None:
    """
    Return active subscription tier distribution as a bar chart dataset.

    Requirements: 4.4, 4.7
    """
    try:
        qs = (
            Subscription.objects.filter(is_active=True)
            .values("tier")
            .annotate(count=Count("id"))
            .order_by("tier")
        )
        labels = [entry["tier"] for entry in qs]
        data = [entry["count"] for entry in qs]
        colors = [
            "oklch(60% .22 262)",
            "oklch(70% .17 265)",
            "oklch(52% .24 260)",
            "oklch(45% .22 262)",
        ]
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Subscriptions",
                    "data": data,
                    "backgroundColor": colors[: len(labels)],
                }
            ],
        }
    except Exception:
        return None


def get_user_registrations_chart_data() -> dict | None:
    """
    Return 30-day user registration trend as a line chart dataset.

    Requirements: 4.5, 4.7
    """
    try:
        thirty_days_ago = timezone.now() - timedelta(days=30)
        qs = (
            User.objects.filter(created_at__gte=thirty_days_ago)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )
        labels = [entry["date"].strftime("%Y-%m-%d") for entry in qs]
        data = [entry["count"] for entry in qs]
        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "New Users",
                    "data": data,
                    "borderColor": "oklch(70% .17 265)",
                    "backgroundColor": "oklch(70% .17 265 / 0.1)",
                }
            ],
        }
    except Exception:
        return None


def _serialize_chart(data: dict | None) -> str | None:
    """JSON-serialize chart data for Unfold chart components, or None on failure."""
    if data is None:
        return None
    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return None


def dashboard_callback(request, context: dict) -> dict:
    """
    Unfold DASHBOARD_CALLBACK entry point.

    Populates the template context with KPI cards and JSON-serialized
    chart datasets ready for Unfold chart components.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """
    context.update(
        {
            "kpi_cards": get_kpi_cards(),
            "ai_requests_chart": _serialize_chart(get_ai_requests_chart_data()),
            "credit_consumption_chart": _serialize_chart(get_credit_consumption_chart_data()),
            "subscription_tier_chart": _serialize_chart(get_subscription_tier_chart_data()),
            "user_registrations_chart": _serialize_chart(get_user_registrations_chart_data()),
        }
    )
    return context
