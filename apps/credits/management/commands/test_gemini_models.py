"""
Django management command to test Gemini API connectivity and list available models.

Usage:
    python manage.py test_gemini_models
"""

import os
from django.core.management.base import BaseCommand
from google import genai
from google.genai.types import HttpOptions


class Command(BaseCommand):
    help = 'Test Gemini API connectivity and list available models'

    def handle(self, *args, **options):
        api_key = os.getenv('GOOGLE_API_KEY', '')
        
        if not api_key:
            self.stdout.write(self.style.ERROR('GOOGLE_API_KEY not found in environment'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'API Key found: {api_key[:10]}...'))
        
        try:
            # Test with v1 API
            self.stdout.write('\n=== Testing with API version v1 ===')
            client_v1 = genai.Client(
                api_key=api_key,
                http_options=HttpOptions(api_version='v1')
            )
            self._test_client(client_v1, 'v1')
            
            # Test with v1beta API
            self.stdout.write('\n=== Testing with API version v1beta ===')
            client_v1beta = genai.Client(
                api_key=api_key,
                http_options=HttpOptions(api_version='v1beta')
            )
            self._test_client(client_v1beta, 'v1beta')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to initialize client: {str(e)}'))
    
    def _test_client(self, client, api_version):
        """Test a client with specific API version."""
        try:
            # List all models
            self.stdout.write(f'\nListing models for API version {api_version}...')
            models_response = client.models.list()
            
            generate_content_models = []
            all_models = []
            
            for model in models_response:
                model_name = model.name
                if model_name.startswith('models/'):
                    model_name = model_name.replace('models/', '')
                
                all_models.append(model_name)
                
                # Check if supports generateContent
                if hasattr(model, 'supported_generation_methods'):
                    methods = model.supported_generation_methods
                    if 'generateContent' in methods:
                        generate_content_models.append(model_name)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ {model_name} (supports: {", ".join(methods)})'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ✗ {model_name} (supports: {", ".join(methods)})'
                            )
                        )
                else:
                    self.stdout.write(f'  ? {model_name} (no method info)')
            
            self.stdout.write(
                f'\nTotal models: {len(all_models)}'
            )
            self.stdout.write(
                f'Models supporting generateContent: {len(generate_content_models)}'
            )
            
            # Test a simple request with the first available model
            if generate_content_models:
                test_model = generate_content_models[0]
                self.stdout.write(f'\n=== Testing generateContent with {test_model} ===')
                
                try:
                    response = client.models.generate_content(
                        model=test_model,
                        contents='Say "Hello, NeuroTwin!" in one sentence.',
                        config={'max_output_tokens': 50, 'temperature': 0.7}
                    )
                    
                    content = response.text if hasattr(response, 'text') else 'No text attribute'
                    self.stdout.write(self.style.SUCCESS(f'Response: {content}'))
                    
                    if hasattr(response, 'usage_metadata'):
                        usage = response.usage_metadata
                        self.stdout.write(
                            f'Tokens used: {getattr(usage, "total_token_count", "N/A")}'
                        )
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Request failed: {str(e)}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to list models: {str(e)}'))
