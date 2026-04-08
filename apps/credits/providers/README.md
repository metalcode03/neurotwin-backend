# Provider Registry

The Provider Registry provides dynamic lookup of AI provider instances for the credit-based AI architecture.

## Overview

The `ProviderRegistry` class maintains a mapping of model names to provider instances and enables the `ModelRouter` to interact with providers through the `AIProvider` interface without knowing implementation details.

## Registered Models

The registry automatically registers the following models on initialization:

- `cerebras` → `CerebrasService`
- `mistral` → `MistralService`
- `gemini-2.5-flash` → `GeminiService(model="gemini-2.5-flash")`
- `gemini-2.5-pro` → `GeminiService(model="gemini-2.5-pro")`
- `gemini-3-pro` → `GeminiService(model="gemini-3-pro")`
- `gemini-3.1-pro` → `GeminiService(model="gemini-3.1-pro")`

## Usage

### Basic Usage

```python
from apps.credits.providers import get_registry

# Get the global registry instance (singleton)
registry = get_registry()

# Get a provider by model name
provider = registry.get_provider('cerebras')

# Use the provider
response = provider.generate_response(
    prompt="Hello, world!",
    max_tokens=100,
    temperature=0.7
)
```

### Check Available Models

```python
# Get list of all registered models
models = registry.get_registered_models()
print(models)  # ['cerebras', 'gemini-2.5-flash', 'gemini-2.5-pro', ...]

# Check if a model is registered
if registry.is_model_registered('gemini-3-pro'):
    provider = registry.get_provider('gemini-3-pro')
```

### Error Handling

```python
from apps.credits.exceptions import ProviderAPIError

try:
    provider = registry.get_provider('unknown-model')
except ProviderAPIError as e:
    print(f"Error: {e}")
    # Error: Model 'unknown-model' is not registered in provider registry.
    # Available models: cerebras, gemini-2.5-flash, ...
```

## Provider Validation

The registry validates all providers on initialization:

- Checks that each provider has required configuration (API keys)
- Logs warnings for providers missing API keys
- Does not fail initialization if API keys are missing (allows graceful degradation)

Validation warnings will appear in logs:

```
[ProviderRegistry] Provider 'cerebras' has no API key configured. Requests to this provider will fail.
```

## Integration with ModelRouter

The `ModelRouter` uses the registry to dynamically select providers:

```python
from apps.credits.providers import get_registry

class ModelRouter:
    def __init__(self):
        self.registry = get_registry()
    
    def select_model(self, brain_mode, operation_type):
        # Determine model name based on routing rules
        model_name = self._apply_routing_rules(brain_mode, operation_type)
        
        # Get provider from registry
        provider = self.registry.get_provider(model_name)
        
        return provider
```

## Requirements Satisfied

- **8.7**: ModelRouter interacts only with AIProvider interface
- **8.8**: All provider implementations registered for dynamic lookup
- **8.10**: Provider availability validated on startup

## Configuration

Providers require API keys in environment variables:

```bash
CEREBRAS_API_KEY=your_cerebras_key
MISTRAL_API_KEY=your_mistral_key
GOOGLE_API_KEY=your_google_key
```

If API keys are not configured, the registry will still initialize but log warnings. Requests to unconfigured providers will fail with authentication errors.
