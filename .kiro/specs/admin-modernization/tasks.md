# Implementation Plan: Admin Modernization

## Overview

Modernize the NeuroTwin Django admin panel by integrating django-unfold, adding NeuroTwin branding, organized sidebar navigation, an analytics dashboard with Chart.js charts, enhanced model list views with colored status badges, and dark mode support. All existing admin registrations and business logic remain intact — only the presentation layer changes.

## Tasks

- [x] 1. Install django-unfold and configure base theme
  - [x] 1.1 Add django-unfold dependency and update INSTALLED_APPS
    - Run `uv add django-unfold` to install the package
    - In `neurotwin/settings.py`, add `"unfold"` and `"unfold.contrib.filters"` to `INSTALLED_APPS` **before** `"django.contrib.admin"`
    - Verify the admin panel loads at `/admin/` with the unfold theme applied
    - _Requirements: 1.1, 1.4_

  - [x] 1.2 Configure UNFOLD settings with NeuroTwin branding
    - Add the `UNFOLD` dictionary to `neurotwin/settings.py` with:
      - `SITE_TITLE`: "NeuroTwin AI Admin"
      - `SITE_HEADER`: "NeuroTwin"
      - `SITE_LOGO` with light/dark mode lambda callables pointing to `static("admin/img/logo-light.svg")` and `static("admin/img/logo-dark.svg")`
      - `SITE_ICON` with light/dark mode variants
      - `SITE_FAVICONS` list
      - `COLORS` dict with NeuroTwin brand palette for primary/font colors
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.1, 6.2, 6.3, 7.1_

  - [x] 1.3 Create static logo and icon assets
    - Create `static/admin/img/logo-light.svg` — NeuroTwin logo for light mode (simple SVG placeholder with "NeuroTwin" text and brain icon)
    - Create `static/admin/img/logo-dark.svg` — NeuroTwin logo for dark mode
    - Create `static/admin/img/icon-light.svg` — Small sidebar icon (light)
    - Create `static/admin/img/icon-dark.svg` — Small sidebar icon (dark)
    - Create `static/admin/img/favicon.svg` — Browser tab favicon
    - _Requirements: 2.2, 6.1_

- [x] 2. Configure sidebar navigation groups
  - [x] 2.1 Add SIDEBAR configuration to UNFOLD settings
    - In the `UNFOLD` dictionary in `neurotwin/settings.py`, add the `SIDEBAR` key with `show_search: True` and `navigation` list containing 8 groups:
      - "Users & Auth" (icon: `people`) → User, VerificationToken, PasswordResetToken
      - "Subscriptions & Billing" (icon: `payments`) → Subscription, SubscriptionHistory, PaymentTransaction, WebhookLog, CreditTopUp
      - "AI & Credits" (icon: `psychology`) → UserCredits, CreditUsageLog, AIRequestLog, BrainRoutingConfig
      - "Twin & Cognition" (icon: `neurology`) → Twin, OnboardingProgress, CSMProfile, CSMChangeLog
      - "Memory & Learning" (icon: `memory`) → MemoryRecord, MemoryAccessLog, LearningEvent
      - "Safety & Audit" (icon: `shield`) → PermissionScope, PermissionHistory, AuditLog
      - "Automation" (icon: `bolt`) → IntegrationTypeModel, AutomationTemplate, Integration, WebhookEvent, Message, Conversation
      - "Voice" (icon: `call`) → VoiceProfile, CallRecord, VoiceApprovalHistory
    - Each model entry uses `reverse_lazy("admin:app_model_changelist")` for the link
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 3. Checkpoint - Verify theme and sidebar
  - Ensure the admin panel loads with unfold theme, branding is visible, sidebar groups are correct. Ask the user if questions arise.

- [x] 4. Migrate admin classes to unfold.admin.ModelAdmin
  - [x] 4.1 Update `apps/authentication/admin.py`
    - Change `UserAdmin` to inherit from both `unfold.admin.ModelAdmin` and `django.contrib.auth.admin.UserAdmin` (multiple inheritance pattern)
    - Change `VerificationTokenAdmin` and `PasswordResetTokenAdmin` to inherit from `unfold.admin.ModelAdmin`
    - Add `@display` decorators for status badges on `is_verified`, `is_active` fields
    - _Requirements: 1.3, 1.4, 5.1_

  - [x] 4.2 Update `apps/subscription/admin.py`
    - Change all admin classes (`SubscriptionAdmin`, `SubscriptionHistoryAdmin`, `PaymentTransactionAdmin`, `WebhookLogAdmin`) to inherit from `unfold.admin.ModelAdmin`
    - Add `@display` decorators for colored status badges on subscription status and payment status fields
    - Add formatted display methods for monetary values (currency prefix)
    - _Requirements: 1.3, 5.1, 5.2_

  - [x] 4.3 Update `apps/credits/admin.py`
    - Change all admin classes (`UserCreditsAdmin`, `CreditUsageLogAdmin`, `AIRequestLogAdmin`, `BrainRoutingConfigAdmin`, `CreditTopUpAdmin`) to inherit from `unfold.admin.ModelAdmin`
    - Add `@display` decorators for colored status badges on AI request status and top-up status fields
    - Add formatted display methods for credit amounts (comma-separated thousands) and timestamps
    - _Requirements: 1.3, 5.1, 5.2_

  - [x] 4.4 Update `apps/csm/admin.py`
    - Change `CSMProfileAdmin` and `CSMChangeLogAdmin` to inherit from `unfold.admin.ModelAdmin`
    - _Requirements: 1.3_

  - [x] 4.5 Update `apps/twin/admin.py`
    - Change `TwinAdmin`, `OnboardingProgressAdmin`, and `AuditLogAdmin` to inherit from `unfold.admin.ModelAdmin`
    - _Requirements: 1.3_

  - [x] 4.6 Update `apps/memory/admin.py`
    - Change `MemoryRecordAdmin` and `MemoryAccessLogAdmin` to inherit from `unfold.admin.ModelAdmin`
    - _Requirements: 1.3_

  - [x] 4.7 Update `apps/learning/admin.py`
    - Change `LearningEventAdmin` to inherit from `unfold.admin.ModelAdmin`
    - _Requirements: 1.3_

  - [x] 4.8 Update `apps/safety/admin.py`
    - Change `PermissionScopeAdmin` and `PermissionHistoryAdmin` to inherit from `unfold.admin.ModelAdmin`
    - _Requirements: 1.3_

  - [x] 4.9 Update `apps/automation/admin.py`
    - Change all admin classes (`IntegrationTypeAdmin`, `AutomationTemplateAdmin`, `IntegrationAdmin`, `WebhookEventAdmin`, `MessageAdmin`, `ConversationAdmin`) to inherit from `unfold.admin.ModelAdmin`
    - Add `@display` decorators for colored status badges on status fields (integration status, webhook event status, message status, conversation status)
    - _Requirements: 1.3, 5.1_

  - [x] 4.10 Update `apps/voice/admin.py`
    - Change `VoiceProfileAdmin`, `CallRecordAdmin`, and `VoiceApprovalHistoryAdmin` to inherit from `unfold.admin.ModelAdmin`
    - _Requirements: 1.3_

- [x] 5. Checkpoint - Verify admin class migration
  - Ensure all admin pages load correctly with unfold styling, status badges render as colored labels, and no existing functionality is broken. Ask the user if questions arise.

- [x] 6. Implement dashboard callback with analytics
  - [x] 6.1 Create `neurotwin/admin_dashboard.py` with KPI query functions
    - Create the module with helper functions:
      - `get_kpi_cards()` → returns list of dicts with total users, active subscriptions, total credits consumed, total AI requests
      - Each query wrapped in try/except returning `"N/A"` on failure
    - Import models: `authentication.User`, `subscription.Subscription`, `credits.CreditUsageLog`, `credits.AIRequestLog`
    - Use `count()` and `aggregate(Sum('credits_consumed'))` for KPI values
    - _Requirements: 4.1, 4.6, 4.7_

  - [x] 6.2 Add chart data query functions to `neurotwin/admin_dashboard.py`
    - `get_ai_requests_chart_data()` → 30-day line chart data using `TruncDate` + `annotate(count)` on `AIRequestLog`
    - `get_credit_consumption_chart_data()` → bar chart data grouped by `brain_mode` using `values('brain_mode').annotate(Sum('credits_consumed'))`
    - `get_subscription_tier_chart_data()` → bar chart data with tier distribution using `filter(is_active=True).values('tier').annotate(count)`
    - `get_user_registrations_chart_data()` → 30-day line chart data using `TruncDate('created_at')` on `User`
    - Each function wrapped in try/except returning `None` on failure
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.7_

  - [x] 6.3 Implement `dashboard_callback` function
    - Create `dashboard_callback(request, context)` that calls all helper functions and updates the context dict
    - Wire it to `UNFOLD["DASHBOARD_CALLBACK"]` in settings
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 6.4 Write property test for KPI summary statistics (Property 1)
    - **Property 1: KPI summary statistics match database state**
    - Generate random sets of users, subscriptions, credit usage logs, and AI request logs using Hypothesis
    - Call KPI functions and assert returned values match actual `count()` / `Sum()` from the database
    - **Validates: Requirements 4.1**

  - [ ]* 6.5 Write property test for time-series aggregation (Property 2)
    - **Property 2: Round trip consistency — time-series aggregation preserves totals and per-day accuracy**
    - Generate random timestamped records within a 30-day window using Hypothesis
    - Call time-series chart data functions and assert: (a) daily counts sum to total records, (b) each day's count matches actual records for that date
    - **Validates: Requirements 4.2, 4.5**

  - [ ]* 6.6 Write property test for grouped aggregation (Property 3)
    - **Property 3: Grouped aggregation matches per-category totals**
    - Generate random credit usage logs with varying `brain_mode` values and credit amounts
    - Call grouped aggregation function and assert per-brain-mode totals match actual `Sum('credits_consumed')` per mode
    - Generate random active subscriptions with varying `tier` values and assert per-tier counts match
    - **Validates: Requirements 4.3, 4.4**

- [x] 7. Create dashboard template
  - [x] 7.1 Create `templates/admin/index.html` dashboard template
    - Extend Unfold's base admin index template
    - Add KPI row: 4 stat cards (total users, active subs, credits consumed, AI requests)
    - Add chart row 1: AI request volume line chart + credit consumption bar chart using Unfold's chart components (`unfold/components/chart/line.html`, `unfold/components/chart/bar.html`)
    - Add chart row 2: subscription tier distribution bar chart + user registrations line chart
    - Add fallback: if chart data is `None`, display a "Data temporarily unavailable" message card
    - Configure `TEMPLATES` dirs in settings to include the project-level `templates/` directory
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.7_

- [ ] 8. Checkpoint - Verify dashboard and charts
  - Ensure the admin dashboard loads with KPI cards and charts rendering correctly. Verify fallback messages appear when data is unavailable. Ask the user if questions arise.

- [-] 9. Add value formatting utilities and tests
  - [ ] 9.1 Create formatting helper functions
    - Create `neurotwin/admin_utils.py` with:
      - `format_credits(amount: int) -> str` — comma-separated thousands (e.g., 1000 → "1,000")
      - `format_currency(amount: float, symbol: str = "$") -> str` — currency prefix formatting
      - `format_timestamp(dt: datetime) -> str` — human-readable timestamp
    - Use these helpers in admin display methods across apps
    - _Requirements: 5.2_

  - [ ]* 9.2 Write property test for value formatting (Property 4)
    - **Property 4: Value formatting produces valid output format**
    - Generate random non-negative integers and assert `format_credits` output contains comma-separated thousands
    - Generate random positive floats and assert `format_currency` output starts with currency symbol
    - Generate random valid datetimes and assert `format_timestamp` returns a non-empty string
    - **Validates: Requirements 5.2**

- [ ] 10. Write unit and integration tests
  - [ ]* 10.1 Write unit tests for admin configuration
    - Test `UNFOLD` dictionary contains required keys (`SITE_TITLE`, `SITE_HEADER`, `SITE_LOGO`, `SIDEBAR`, `DASHBOARD_CALLBACK`)
    - Test all admin classes inherit from `unfold.admin.ModelAdmin` by iterating `admin.site._registry`
    - Test all expected models from all 11 apps are registered in admin
    - Test sidebar configuration has 8 navigation groups with correct titles and distinct icons
    - _Requirements: 1.1, 1.3, 1.4, 2.1, 2.4, 3.1, 3.3_

  - [ ]* 10.2 Write unit tests for dashboard error handling
    - Mock database queries to raise exceptions
    - Assert `get_kpi_cards()` returns fallback values (`"N/A"`) on failure
    - Assert chart data functions return `None` on failure
    - _Requirements: 4.7_

  - [ ]* 10.3 Write integration tests for admin page loading
    - Use Django test client with an admin user to verify admin index page returns 200
    - Verify response contains "NeuroTwin AI Admin" text
    - Verify login page contains NeuroTwin branding text
    - _Requirements: 2.1, 2.3, 6.2_

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Run `uv run pytest` and ensure all tests pass. Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The implementation language is Python (Django 6.0+ / Python 3.13+)
- django-unfold's `ModelAdmin` extends Django's `ModelAdmin`, so all existing admin configurations (list_display, list_filter, search_fields, fieldsets, etc.) continue to work without modification
- Property tests use Hypothesis (already in dev dependencies)
- No new database models are introduced — this is purely a presentation-layer change
