"""
Property-based tests for admin dashboard KPI summary statistics.

Feature: admin-modernization, Property 1: KPI summary statistics match database state

For any set of users, subscriptions, credit usage logs, and AI request logs
in the database, the KPI card values returned by ``get_kpi_cards()`` SHALL
equal the actual count() of users, count() of active subscriptions,
Sum('credits_consumed') of credit usage logs, and count() of AI request logs.

Validates: Requirements 4.1
"""

from hypothesis import given, strategies as st, settings as h_settings
from hypothesis.extra.django import TestCase
from django.db.models import Sum

from apps.authentication.models import User
from apps.credits.models import AIRequestLog, CreditUsageLog
from apps.subscription.models import Subscription, SubscriptionTier
from neurotwin.admin_dashboard import get_kpi_cards


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

count_strategy = st.integers(min_value=0, max_value=5)
credits_consumed_strategy = st.integers(min_value=1, max_value=10_000)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_user_counter = 0


def _next_email() -> str:
    global _user_counter
    _user_counter += 1
    return f"kpi_prop_{_user_counter}@test.neurotwin.io"


def _cards_to_dict(cards: list[dict]) -> dict[str, object]:
    """Convert the KPI cards list into a title → metric mapping."""
    return {card["title"]: card["metric"] for card in cards}


def _wipe() -> None:
    """Delete all rows created during a single Hypothesis example."""
    CreditUsageLog.objects.all().delete()
    AIRequestLog.objects.all().delete()
    Subscription.objects.all().delete()
    User.objects.filter(email__endswith="@test.neurotwin.io").delete()


# ---------------------------------------------------------------------------
# Property test — uses Django TestCase for per-example rollback
# ---------------------------------------------------------------------------


class TestKPISummaryStatistics(TestCase):
    """
    Property 1: KPI summary statistics match database state.

    *For any* set of users, subscriptions, credit usage logs, and AI request
    logs in the database, the KPI card values returned by ``get_kpi_cards()``
    SHALL equal the actual ``count()`` / ``Sum()`` from the database.

    Feature: admin-modernization, Property 1: KPI summary statistics match database state
    Validates: Requirements 4.1
    """

    @given(
        n_extra_users=count_strategy,
        n_active_subs=count_strategy,
        n_inactive_subs=count_strategy,
        n_credit_logs=count_strategy,
        n_ai_requests=count_strategy,
        credit_amounts=st.lists(
            credits_consumed_strategy, min_size=0, max_size=5
        ),
    )
    @h_settings(max_examples=10, deadline=None)
    def test_kpi_values_match_database(
        self,
        n_extra_users: int,
        n_active_subs: int,
        n_inactive_subs: int,
        n_credit_logs: int,
        n_ai_requests: int,
        credit_amounts: list[int],
    ) -> None:
        """KPI card values must exactly reflect the current database state."""
        _wipe()

        try:
            # We need enough users for all FK references.
            n_needed = max(
                1,
                n_active_subs + n_inactive_subs,
                n_credit_logs,
                n_ai_requests,
            )
            total_users = n_needed + n_extra_users

            users: list[User] = []
            for _ in range(total_users):
                users.append(
                    User.objects.create_user(email=_next_email(), password="pw")
                )

            # --- Subscriptions (active + inactive) ---------------------
            for i in range(n_active_subs):
                Subscription.objects.create(
                    user=users[i], tier=SubscriptionTier.PRO, is_active=True,
                )
            for i in range(n_inactive_subs):
                idx = n_active_subs + i
                if idx < len(users):
                    Subscription.objects.create(
                        user=users[idx],
                        tier=SubscriptionTier.FREE,
                        is_active=False,
                    )

            # --- Credit usage logs -------------------------------------
            for i in range(n_credit_logs):
                amount = credit_amounts[i] if i < len(credit_amounts) else 1
                CreditUsageLog.objects.create(
                    user=users[i % len(users)],
                    credits_consumed=amount,
                    operation_type="simple_response",
                    brain_mode="brain",
                    model_used="gemini-3-flash",
                )

            # --- AI request logs ---------------------------------------
            for i in range(n_ai_requests):
                AIRequestLog.objects.create(
                    user=users[i % len(users)],
                    brain_mode="brain",
                    operation_type="simple_response",
                    model_used="gemini-3-flash",
                    prompt_length=100,
                    status="success",
                )

            # --- Expected values (ground truth from DB) ----------------
            expected_users = User.objects.count()
            expected_active_subs = Subscription.objects.filter(
                is_active=True
            ).count()
            agg = CreditUsageLog.objects.aggregate(
                total=Sum("credits_consumed")
            )
            expected_credits = agg["total"] or 0
            expected_ai_requests = AIRequestLog.objects.count()

            # --- Function under test -----------------------------------
            cards = get_kpi_cards()
            kpi = _cards_to_dict(cards)

            # --- Assertions --------------------------------------------
            assert kpi["Total Users"] == expected_users
            assert kpi["Active Subscriptions"] == expected_active_subs
            assert kpi["Credits Consumed"] == expected_credits
            assert kpi["AI Requests"] == expected_ai_requests

        finally:
            _wipe()
