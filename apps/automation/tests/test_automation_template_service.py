"""
Unit tests for AutomationTemplateService.

Tests template validation, variable substitution, workflow instantiation,
and error messages.

Requirements: 6.1-6.7, 16.2-16.3, 16.7
"""

import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.automation.models import (
    IntegrationTypeModel,
    IntegrationCategory,
    Integration,
    AutomationTemplate,
    TriggerType,
    Workflow,
)
from apps.automation.services.automation_template import AutomationTemplateService


User = get_user_model()


class AutomationTemplateServiceTestCase(TestCase):
    """Test suite for AutomationTemplateService."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Get or create test integration type (migration may have created it)
        self.integration_type, _ = IntegrationTypeModel.objects.get_or_create(
            type='gmail',
            defaults={
                'name': 'Gmail',
                'description': 'Gmail integration for email management',
                'brief_description': 'Email management',
                'category': IntegrationCategory.COMMUNICATION,
                'oauth_config': {
                    'client_id': 'test_client_id',
                    'authorization_url': 'https://accounts.google.com/o/oauth2/auth',
                    'token_url': 'https://oauth2.googleapis.com/token',
                    'scopes': ['email', 'profile']
                },
                'is_active': True
            }
        )
        
        # Create test integration for user
        self.integration = Integration.objects.create(
            user=self.user,
            integration_type=self.integration_type,
            scopes=['email', 'profile'],
            is_active=True
        )
        
        # Valid step structure for tests
        self.valid_steps = [
            {
                'action_type': 'send_email',
                'integration_type_id': str(self.integration_type.id),
                'parameters': {
                    'to': '{{user.email}}',
                    'subject': 'Test Email',
                    'body': 'Hello {{user.email}}'
                }
            }
        ]


class CreateTemplateTests(AutomationTemplateServiceTestCase):
    """Tests for create_template method."""
    
    def test_create_template_success(self):
        """Test successful template creation with valid data."""
        template = AutomationTemplateService.create_template(
            integration_type_id=self.integration_type.id,
            name='Daily Email Summary',
            description='Send daily email summary',
            trigger_type=TriggerType.SCHEDULED,
            trigger_config={'schedule': '0 9 * * *'},
            steps=self.valid_steps,
            is_enabled_by_default=True
        )
        
        self.assertIsNotNone(template)
        self.assertEqual(template.name, 'Daily Email Summary')
        self.assertEqual(template.trigger_type, TriggerType.SCHEDULED)
        self.assertEqual(template.integration_type, self.integration_type)
        self.assertTrue(template.is_enabled_by_default)
        self.assertTrue(template.is_active)
        self.assertEqual(len(template.get_steps_list()), 1)
    
    def test_create_template_missing_name(self):
        """Test template creation fails with missing name."""
        with self.assertRaises(ValidationError) as context:
            AutomationTemplateService.create_template(
                integration_type_id=self.integration_type.id,
                name='',
                description='Test description',
                trigger_type=TriggerType.SCHEDULED,
                trigger_config={},
                steps=self.valid_steps
            )
        
        self.assertIn('name is required', str(context.exception))
    
    def test_create_template_missing_trigger_type(self):
        """Test template creation fails with missing trigger type."""
        with self.assertRaises(ValidationError) as context:
            AutomationTemplateService.create_template(
                integration_type_id=self.integration_type.id,
                name='Test Template',
                description='Test description',
                trigger_type='',
                trigger_config={},
                steps=self.valid_steps
            )
        
        self.assertIn('Trigger type is required', str(context.exception))
    
    def test_create_template_invalid_trigger_type(self):
        """Test template creation fails with invalid trigger type."""
        with self.assertRaises(ValidationError) as context:
            AutomationTemplateService.create_template(
                integration_type_id=self.integration_type.id,
                name='Test Template',
                description='Test description',
                trigger_type='invalid_type',
                trigger_config={},
                steps=self.valid_steps
            )
        
        self.assertIn('Trigger type must be one of', str(context.exception))
    
    def test_create_template_empty_steps(self):
        """Test template creation fails with empty steps."""
        with self.assertRaises(ValidationError) as context:
            AutomationTemplateService.create_template(
                integration_type_id=self.integration_type.id,
                name='Test Template',
                description='Test description',
                trigger_type=TriggerType.MANUAL,
                trigger_config={},
                steps=[]
            )
        
        self.assertIn('At least one step is required', str(context.exception))
    
    def test_create_template_invalid_step_structure(self):
        """Test template creation fails with invalid step structure."""
        invalid_steps = [
            {
                'action_type': 'send_email',
                # Missing integration_type_id
                'parameters': {}
            }
        ]
        
        with self.assertRaises(ValidationError) as context:
            AutomationTemplateService.create_template(
                integration_type_id=self.integration_type.id,
                name='Test Template',
                description='Test description',
                trigger_type=TriggerType.MANUAL,
                trigger_config={},
                steps=invalid_steps
            )
        
        self.assertIn('Invalid template structure', str(context.exception))
        self.assertIn('integration_type_id', str(context.exception))
    
    def test_create_template_nonexistent_integration_type(self):
        """Test template creation fails with nonexistent integration type."""
        fake_id = uuid.uuid4()
        
        with self.assertRaises(IntegrationTypeModel.DoesNotExist):
            AutomationTemplateService.create_template(
                integration_type_id=fake_id,
                name='Test Template',
                description='Test description',
                trigger_type=TriggerType.MANUAL,
                trigger_config={},
                steps=self.valid_steps
            )


class ValidateTemplateStructureTests(AutomationTemplateServiceTestCase):
    """Tests for validate_template_structure method."""
    
    def test_validate_valid_structure(self):
        """Test validation passes for valid template structure."""
        template = {
            'steps': [
                {
                    'action_type': 'send_email',
                    'integration_type_id': str(self.integration_type.id),
                    'parameters': {'to': 'test@example.com'}
                }
            ]
        }
        
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_missing_steps_field(self):
        """Test validation fails when steps field is missing."""
        template = {}
        
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertFalse(is_valid)
        self.assertIn("Template must contain 'steps' field", errors)
    
    def test_validate_steps_not_list(self):
        """Test validation fails when steps is not a list."""
        template = {'steps': 'not a list'}
        
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertFalse(is_valid)
        self.assertIn('Steps must be a list', errors)
    
    def test_validate_empty_steps_list(self):
        """Test validation fails with empty steps list."""
        template = {'steps': []}
        
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertFalse(is_valid)
        self.assertIn('At least one step is required', errors)
    
    def test_validate_step_not_dict(self):
        """Test validation fails when step is not a dictionary."""
        template = {'steps': ['not a dict']}
        
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertFalse(is_valid)
        self.assertIn('Step 0: must be a dictionary', errors)
    
    def test_validate_step_missing_action_type(self):
        """Test validation fails when step is missing action_type."""
        template = {
            'steps': [
                {
                    'integration_type_id': str(self.integration_type.id),
                    'parameters': {}
                }
            ]
        }
        
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertFalse(is_valid)
        self.assertIn("Step 0: missing required field 'action_type'", errors)
    
    def test_validate_step_missing_integration_type_id(self):
        """Test validation fails when step is missing integration_type_id."""
        template = {
            'steps': [
                {
                    'action_type': 'send_email',
                    'parameters': {}
                }
            ]
        }
        
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertFalse(is_valid)
        self.assertIn("Step 0: missing required field 'integration_type_id'", errors)
    
    def test_validate_step_empty_action_type(self):
        """Test validation fails when action_type is empty."""
        template = {
            'steps': [
                {
                    'action_type': '',
                    'integration_type_id': str(self.integration_type.id),
                    'parameters': {}
                }
            ]
        }
        
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertFalse(is_valid)
        self.assertIn("Step 0: 'action_type' cannot be empty", errors)
    
    def test_validate_step_empty_integration_type_id(self):
        """Test validation fails when integration_type_id is empty."""
        template = {
            'steps': [
                {
                    'action_type': 'send_email',
                    'integration_type_id': '',
                    'parameters': {}
                }
            ]
        }
        
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertFalse(is_valid)
        self.assertIn("Step 0: 'integration_type_id' cannot be empty", errors)
    
    def test_validate_step_non_string_integration_type_id(self):
        """Test validation fails when integration_type_id is not a string."""
        template = {
            'steps': [
                {
                    'action_type': 'send_email',
                    'integration_type_id': 123,
                    'parameters': {}
                }
            ]
        }
        
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertFalse(is_valid)
        self.assertIn("Step 0: 'integration_type_id' must be a string", errors)
    
    def test_validate_multiple_steps_with_errors(self):
        """Test validation collects errors from multiple steps."""
        template = {
            'steps': [
                {
                    'action_type': 'send_email',
                    # Missing integration_type_id
                },
                {
                    # Missing action_type
                    'integration_type_id': str(self.integration_type.id),
                },
                {
                    'action_type': '',
                    'integration_type_id': '',
                }
            ]
        }
        
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 3)
        self.assertTrue(any('Step 0' in error for error in errors))
        self.assertTrue(any('Step 1' in error for error in errors))
        self.assertTrue(any('Step 2' in error for error in errors))


class ParseTemplateVariablesTests(AutomationTemplateServiceTestCase):
    """Tests for parse_template_variables method."""
    
    def test_parse_user_email_variable(self):
        """Test parsing {{user.email}} variable."""
        template_config = {
            'to': '{{user.email}}',
            'subject': 'Test'
        }
        
        result = AutomationTemplateService.parse_template_variables(
            template_config,
            self.user,
            self.integration
        )
        
        self.assertEqual(result['to'], self.user.email)
        self.assertEqual(result['subject'], 'Test')
    
    def test_parse_user_email_in_body_variable(self):
        """Test parsing {{user.email}} in body variable."""
        template_config = {
            'greeting': 'Hello {{user.email}}'
        }
        
        result = AutomationTemplateService.parse_template_variables(
            template_config,
            self.user,
            self.integration
        )
        
        self.assertEqual(result['greeting'], f'Hello {self.user.email}')
    
    def test_parse_user_id_variable(self):
        """Test parsing {{user.id}} variable."""
        template_config = {
            'user_id': '{{user.id}}'
        }
        
        result = AutomationTemplateService.parse_template_variables(
            template_config,
            self.user,
            self.integration
        )
        
        self.assertEqual(result['user_id'], self.user.id)
    
    def test_parse_integration_id_variable(self):
        """Test parsing {{integration.id}} variable."""
        template_config = {
            'integration_id': '{{integration.id}}'
        }
        
        result = AutomationTemplateService.parse_template_variables(
            template_config,
            self.user,
            self.integration
        )
        
        self.assertEqual(result['integration_id'], str(self.integration.id))
    
    def test_parse_integration_user_id_variable(self):
        """Test parsing {{integration.user_id}} variable."""
        template_config = {
            'user_id': '{{integration.user_id}}'
        }
        
        result = AutomationTemplateService.parse_template_variables(
            template_config,
            self.user,
            self.integration
        )
        
        self.assertEqual(result['user_id'], self.integration.user_id)
    
    def test_parse_multiple_variables(self):
        """Test parsing multiple variables in same config."""
        template_config = {
            'to': '{{user.email}}',
            'from': 'noreply@example.com',
            'subject': 'Hello {{user.email}}',
            'body': 'Your ID is {{user.id}}'
        }
        
        result = AutomationTemplateService.parse_template_variables(
            template_config,
            self.user,
            self.integration
        )
        
        self.assertEqual(result['to'], self.user.email)
        self.assertEqual(result['from'], 'noreply@example.com')
        self.assertEqual(result['subject'], f'Hello {self.user.email}')
        self.assertEqual(result['body'], f'Your ID is {self.user.id}')
    
    def test_parse_boolean_variable(self):
        """Test parsing boolean values."""
        template_config = {
            'is_active': '{{integration.is_active}}'
        }
        
        result = AutomationTemplateService.parse_template_variables(
            template_config,
            self.user,
            self.integration
        )
        
        self.assertEqual(result['is_active'], self.integration.is_active)
    
    def test_parse_nonexistent_variable(self):
        """Test parsing nonexistent variable returns None."""
        template_config = {
            'value': '{{user.nonexistent_field}}'
        }
        
        result = AutomationTemplateService.parse_template_variables(
            template_config,
            self.user,
            self.integration
        )
        
        self.assertIsNone(result['value'])
    
    def test_parse_invalid_root_variable(self):
        """Test parsing variable with invalid root returns None."""
        template_config = {
            'value': '{{invalid.field}}'
        }
        
        result = AutomationTemplateService.parse_template_variables(
            template_config,
            self.user,
            self.integration
        )
        
        self.assertIsNone(result['value'])
    
    def test_parse_nested_dict_config(self):
        """Test parsing variables in nested dictionary."""
        template_config = {
            'email': {
                'to': '{{user.email}}',
                'subject': 'Hello {{user.email}}'
            },
            'metadata': {
                'user_id': '{{user.id}}'
            }
        }
        
        result = AutomationTemplateService.parse_template_variables(
            template_config,
            self.user,
            self.integration
        )
        
        self.assertEqual(result['email']['to'], self.user.email)
        self.assertEqual(result['email']['subject'], f'Hello {self.user.email}')
        self.assertEqual(result['metadata']['user_id'], self.user.id)
    
    def test_parse_variables_in_list(self):
        """Test parsing variables within list values."""
        template_config = {
            'recipients': ['{{user.email}}', 'admin@example.com']
        }
        
        result = AutomationTemplateService.parse_template_variables(
            template_config,
            self.user,
            self.integration
        )
        
        self.assertEqual(result['recipients'][0], self.user.email)
        self.assertEqual(result['recipients'][1], 'admin@example.com')


class InstantiateTemplatesForUserTests(AutomationTemplateServiceTestCase):
    """Tests for instantiate_templates_for_user method."""
    
    def test_instantiate_single_template(self):
        """Test instantiating a single template for user."""
        # Create template
        template = AutomationTemplate.objects.create(
            integration_type=self.integration_type,
            name='Daily Summary',
            description='Send daily summary email',
            trigger_type=TriggerType.SCHEDULED,
            trigger_config={'schedule': '0 9 * * *'},
            steps=[
                {
                    'action_type': 'send_email',
                    'integration_type_id': str(self.integration_type.id),
                    'parameters': {
                        'to': '{{user.email}}',
                        'subject': 'Daily Summary for {{user.email}}'
                    }
                }
            ],
            is_enabled_by_default=True,
            is_active=True
        )
        
        # Instantiate templates
        workflows = AutomationTemplateService.instantiate_templates_for_user(
            self.user,
            self.integration
        )
        
        self.assertEqual(len(workflows), 1)
        workflow = workflows[0]
        
        self.assertEqual(workflow.user, self.user)
        self.assertEqual(workflow.automation_template, template)
        self.assertEqual(workflow.name, template.name)
        self.assertFalse(workflow.is_custom)
        self.assertTrue(workflow.is_active)
        self.assertFalse(workflow.last_modified_by_twin)
        self.assertEqual(workflow.twin_modification_count, 0)
    
    def test_instantiate_multiple_templates(self):
        """Test instantiating multiple templates for user."""
        # Create multiple templates
        template1 = AutomationTemplate.objects.create(
            integration_type=self.integration_type,
            name='Template 1',
            description='First template',
            trigger_type=TriggerType.SCHEDULED,
            trigger_config={},
            steps=self.valid_steps,
            is_active=True
        )
        
        template2 = AutomationTemplate.objects.create(
            integration_type=self.integration_type,
            name='Template 2',
            description='Second template',
            trigger_type=TriggerType.EVENT_DRIVEN,
            trigger_config={},
            steps=self.valid_steps,
            is_active=True
        )
        
        # Instantiate templates
        workflows = AutomationTemplateService.instantiate_templates_for_user(
            self.user,
            self.integration
        )
        
        self.assertEqual(len(workflows), 2)
        workflow_names = [w.name for w in workflows]
        self.assertIn('Template 1', workflow_names)
        self.assertIn('Template 2', workflow_names)
    
    def test_instantiate_with_variable_substitution(self):
        """Test template instantiation performs variable substitution."""
        # Create template with variables
        template = AutomationTemplate.objects.create(
            integration_type=self.integration_type,
            name='Welcome Email',
            description='Send welcome email',
            trigger_type=TriggerType.MANUAL,
            trigger_config={'user_id': '{{user.id}}'},
            steps=[
                {
                    'action_type': 'send_email',
                    'integration_type_id': str(self.integration_type.id),
                    'parameters': {
                        'to': '{{user.email}}',
                        'subject': 'Welcome {{user.email}}!'
                    }
                }
            ],
            is_active=True
        )
        
        # Instantiate templates
        workflows = AutomationTemplateService.instantiate_templates_for_user(
            self.user,
            self.integration
        )
        
        self.assertEqual(len(workflows), 1)
        workflow = workflows[0]
        
        # Check trigger_config substitution
        self.assertEqual(workflow.trigger_config['user_id'], self.user.id)
        
        # Check steps substitution
        step = workflow.get_steps_list()[0]
        self.assertEqual(step['parameters']['to'], self.user.email)
        self.assertEqual(step['parameters']['subject'], f'Welcome {self.user.email}!')
    
    def test_instantiate_only_active_templates(self):
        """Test only active templates are instantiated."""
        # Create active template
        active_template = AutomationTemplate.objects.create(
            integration_type=self.integration_type,
            name='Active Template',
            description='Active',
            trigger_type=TriggerType.MANUAL,
            trigger_config={},
            steps=self.valid_steps,
            is_active=True
        )
        
        # Create inactive template
        inactive_template = AutomationTemplate.objects.create(
            integration_type=self.integration_type,
            name='Inactive Template',
            description='Inactive',
            trigger_type=TriggerType.MANUAL,
            trigger_config={},
            steps=self.valid_steps,
            is_active=False
        )
        
        # Instantiate templates
        workflows = AutomationTemplateService.instantiate_templates_for_user(
            self.user,
            self.integration
        )
        
        self.assertEqual(len(workflows), 1)
        self.assertEqual(workflows[0].name, 'Active Template')
    
    def test_instantiate_respects_enabled_by_default(self):
        """Test workflow is_active respects template is_enabled_by_default."""
        # Create template enabled by default
        enabled_template = AutomationTemplate.objects.create(
            integration_type=self.integration_type,
            name='Enabled Template',
            description='Enabled by default',
            trigger_type=TriggerType.MANUAL,
            trigger_config={},
            steps=self.valid_steps,
            is_enabled_by_default=True,
            is_active=True
        )
        
        # Create template disabled by default
        disabled_template = AutomationTemplate.objects.create(
            integration_type=self.integration_type,
            name='Disabled Template',
            description='Disabled by default',
            trigger_type=TriggerType.MANUAL,
            trigger_config={},
            steps=self.valid_steps,
            is_enabled_by_default=False,
            is_active=True
        )
        
        # Instantiate templates
        workflows = AutomationTemplateService.instantiate_templates_for_user(
            self.user,
            self.integration
        )
        
        self.assertEqual(len(workflows), 2)
        
        enabled_workflow = next(w for w in workflows if w.name == 'Enabled Template')
        disabled_workflow = next(w for w in workflows if w.name == 'Disabled Template')
        
        self.assertTrue(enabled_workflow.is_active)
        self.assertFalse(disabled_workflow.is_active)
    
    def test_instantiate_no_templates(self):
        """Test instantiation with no templates returns empty list."""
        # Don't create any templates
        
        workflows = AutomationTemplateService.instantiate_templates_for_user(
            self.user,
            self.integration
        )
        
        self.assertEqual(len(workflows), 0)
    
    def test_instantiate_only_matching_integration_type(self):
        """Test only templates for matching integration type are instantiated."""
        # Create template for Gmail
        gmail_template = AutomationTemplate.objects.create(
            integration_type=self.integration_type,
            name='Gmail Template',
            description='Gmail specific',
            trigger_type=TriggerType.MANUAL,
            trigger_config={},
            steps=self.valid_steps,
            is_active=True
        )
        
        # Get or create another integration type
        slack_type, _ = IntegrationTypeModel.objects.get_or_create(
            type='slack',
            defaults={
                'name': 'Slack',
                'description': 'Slack integration',
                'brief_description': 'Team chat',
                'category': IntegrationCategory.COMMUNICATION,
                'is_active': True
            }
        )
        
        # Create template for Slack
        slack_template = AutomationTemplate.objects.create(
            integration_type=slack_type,
            name='Slack Template',
            description='Slack specific',
            trigger_type=TriggerType.MANUAL,
            trigger_config={},
            steps=[
                {
                    'action_type': 'send_message',
                    'integration_type_id': str(slack_type.id),
                    'parameters': {}
                }
            ],
            is_active=True
        )
        
        # Instantiate templates for Gmail integration
        workflows = AutomationTemplateService.instantiate_templates_for_user(
            self.user,
            self.integration
        )
        
        self.assertEqual(len(workflows), 1)
        self.assertEqual(workflows[0].name, 'Gmail Template')


class ErrorMessageTests(AutomationTemplateServiceTestCase):
    """Tests for descriptive error messages."""
    
    def test_error_message_missing_name(self):
        """Test error message is descriptive for missing name."""
        with self.assertRaises(ValidationError) as context:
            AutomationTemplateService.create_template(
                integration_type_id=self.integration_type.id,
                name='',
                description='Test',
                trigger_type=TriggerType.MANUAL,
                trigger_config={},
                steps=self.valid_steps
            )
        
        error_message = str(context.exception)
        self.assertIn('Template name is required', error_message)
    
    def test_error_message_invalid_trigger_type(self):
        """Test error message lists valid trigger types."""
        with self.assertRaises(ValidationError) as context:
            AutomationTemplateService.create_template(
                integration_type_id=self.integration_type.id,
                name='Test',
                description='Test',
                trigger_type='invalid',
                trigger_config={},
                steps=self.valid_steps
            )
        
        error_message = str(context.exception)
        self.assertIn('Trigger type must be one of', error_message)
        self.assertIn('scheduled', error_message)
        self.assertIn('event_driven', error_message)
        self.assertIn('manual', error_message)
    
    def test_error_message_invalid_structure(self):
        """Test error message describes structure problems."""
        invalid_steps = [
            {
                'action_type': '',
                'integration_type_id': ''
            }
        ]
        
        with self.assertRaises(ValidationError) as context:
            AutomationTemplateService.create_template(
                integration_type_id=self.integration_type.id,
                name='Test',
                description='Test',
                trigger_type=TriggerType.MANUAL,
                trigger_config={},
                steps=invalid_steps
            )
        
        error_message = str(context.exception)
        self.assertIn('Invalid template structure', error_message)
        self.assertIn('action_type', error_message)
        self.assertIn('integration_type_id', error_message)
    
    def test_error_message_step_index_in_validation(self):
        """Test validation errors include step index."""
        invalid_steps = [
            {
                'action_type': 'valid',
                'integration_type_id': str(self.integration_type.id)
            },
            {
                'action_type': '',  # Invalid
                'integration_type_id': str(self.integration_type.id)
            }
        ]
        
        template = {'steps': invalid_steps}
        is_valid, errors = AutomationTemplateService.validate_template_structure(template)
        
        self.assertFalse(is_valid)
        self.assertTrue(any('Step 1' in error for error in errors))