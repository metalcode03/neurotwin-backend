"""
Management command to seed default Brain routing configuration.

Creates the default BrainRoutingConfig with production routing rules.
Requirements: 6.9
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.credits.models import BrainRoutingConfig
from apps.credits.constants import ROUTING_RULES


class Command(BaseCommand):
    help = 'Seed default Brain routing configuration'
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update if default config already exists',
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        force = options.get('force', False)
        
        config_name = 'default_production'
        
        # Check if default config already exists
        existing_config = BrainRoutingConfig.objects.filter(
            config_name=config_name
        ).first()
        
        if existing_config and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'Default routing config "{config_name}" already exists. '
                    f'Use --force to update.'
                )
            )
            return
        
        try:
            with transaction.atomic():
                if existing_config:
                    # Update existing config
                    existing_config.routing_rules = ROUTING_RULES
                    existing_config.is_active = True
                    existing_config.save()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Updated routing config "{config_name}"'
                        )
                    )
                else:
                    # Create new config
                    config = BrainRoutingConfig.objects.create(
                        config_name=config_name,
                        routing_rules=ROUTING_RULES,
                        is_active=True,
                        created_by=None,  # System-created
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created routing config "{config_name}" (ID: {config.id})'
                        )
                    )
                
                # Display routing rules summary
                self._display_routing_summary()
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Error seeding routing config: {e}'
                )
            )
            raise
    
    def _display_routing_summary(self):
        """Display summary of routing rules."""
        self.stdout.write('\nRouting Rules Summary:')
        self.stdout.write('-' * 60)
        
        for brain_mode, operations in ROUTING_RULES.items():
            self.stdout.write(f'\n{brain_mode.upper()}:')
            for operation_type, model in operations.items():
                self.stdout.write(f'  {operation_type:20} → {model}')
        
        self.stdout.write('\n' + '-' * 60)
        
        # Count unique models
        unique_models = set()
        for operations in ROUTING_RULES.values():
            unique_models.update(operations.values())
        
        self.stdout.write(
            f'\nTotal routes: {sum(len(ops) for ops in ROUTING_RULES.values())}'
        )
        self.stdout.write(f'Unique models: {len(unique_models)}')
        self.stdout.write(f'Models: {", ".join(sorted(unique_models))}')
