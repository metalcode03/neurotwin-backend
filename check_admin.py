import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurotwin.settings')
django.setup()

from django.contrib import admin
from apps.credits.models import UserCredits, CreditUsageLog, AIRequestLog, BrainRoutingConfig, CreditTopUp

print("Checking admin registration...")
models = [UserCredits, CreditUsageLog, AIRequestLog, BrainRoutingConfig, CreditTopUp]

for model in models:
    is_registered = admin.site.is_registered(model)
    print(f"{model.__name__}: {'✓ Registered' if is_registered else '✗ NOT registered'}")

print("\nAll registered models in admin:")
for model, model_admin in admin.site._registry.items():
    if 'credits' in model._meta.app_label:
        print(f"  - {model._meta.app_label}.{model.__name__}")
