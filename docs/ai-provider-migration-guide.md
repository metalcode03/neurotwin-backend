# AI Provider Migration Guide

## For Developers Using AIService

### No Changes Required! 🎉

If you're using `AIService.process_request()`, you don't need to change anything. The refactoring is internal to the provider layer.

```python
# This still works exactly the same
from apps.credits.ai_service import AIService
from apps.credits.enums import BrainMode, OperationType

ai_service = AIService()
response = ai_service.process_request(
    user_id=user.id,
    prompt="What is the weather like?",
    brain_mode=BrainMode.BRAIN,
    operation_type=OperationType.SIMPLE_RESPONSE,
    max_tokens=500,
    temperature=0.7
)

print(response.content)
```

## For Developers Creating New Providers

### Old Interface (DEPRECATED)

```python
class MyProvider(AIProvider):
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> ProviderResponse:
        # Build messages internally
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Call API...
```

### New Interface (REQUIRED)

```python
class MyProvider(AIProvider):
    def generate_response(
        self,
        messages: List[dict],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> ProviderResponse:
        """
        Args:
            messages: List of message dicts with 'role' and 'content' keys
                     Example: [
                         {"role": "system", "content": "You are helpful"},
                         {"role": "user", "content": "Hello"}
                     ]
        """
        # Translate messages to your provider's format
        # Option 1: OpenAI-style (Mistral, Cerebras, etc.)
        response = api.chat.completions.create(
            model=self.model,
            messages=messages,  # Pass directly
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Option 2: Custom format (Gemini, etc.)
        formatted_prompt = self._format_messages(messages)
        response = api.generate(
            prompt=formatted_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
```

## Message Format Specification

### Standard Format
```python
messages = [
    {"role": "system", "content": "System instructions here"},
    {"role": "user", "content": "User message here"},
    {"role": "assistant", "content": "Previous assistant response"},
    {"role": "user", "content": "Follow-up user message"}
]
```

### Supported Roles
- `system`: System-level instructions (optional, usually first)
- `user`: User messages
- `assistant`: Assistant responses (for multi-turn conversations)

### Rules
1. Messages array may be empty (handle gracefully)
2. System message is optional
3. Multiple user/assistant turns may exist
4. Order matters - process sequentially

## Provider-Specific Examples

### OpenAI-Compatible APIs (Mistral, Cerebras, OpenAI, etc.)

```python
def generate_response(self, messages: List[dict], max_tokens: int, temperature: float):
    # These APIs accept messages directly
    response = self.client.chat.completions.create(
        model=self.model,
        messages=messages,  # Pass as-is
        max_tokens=max_tokens,
        temperature=temperature
    )
    return self._parse_response(response)
```

### Gemini (Custom Format)

```python
def generate_response(self, messages: List[dict], max_tokens: int, temperature: float):
    # Gemini needs a single formatted string
    contents = self._format_messages_for_gemini(messages)
    
    response = self.client.models.generate_content(
        model=self.api_model_id,
        contents=contents,  # Single string
        config={
            'max_output_tokens': max_tokens,
            'temperature': temperature,
            # NO system_instruction - it's invalid!
        }
    )
    return self._parse_response(response)

def _format_messages_for_gemini(self, messages: List[dict]) -> str:
    formatted = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            formatted.append(f"[SYSTEM INSTRUCTIONS]\n{content}")
        elif role == "user":
            formatted.append(f"[USER]\n{content}")
        elif role == "assistant":
            formatted.append(f"[ASSISTANT]\n{content}")
    
    return "\n\n".join(formatted)
```

### Anthropic Claude (Example)

```python
def generate_response(self, messages: List[dict], max_tokens: int, temperature: float):
    # Claude separates system from messages
    system_content = None
    conversation_messages = []
    
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        else:
            conversation_messages.append(msg)
    
    response = self.client.messages.create(
        model=self.model,
        system=system_content,  # Separate parameter
        messages=conversation_messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
    return self._parse_response(response)
```

## Testing Your Provider

```python
def test_provider_with_messages():
    provider = MyProvider()
    
    # Test with system prompt
    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"}
    ]
    response = provider.generate_response(messages, max_tokens=100, temperature=0.7)
    assert response.content
    
    # Test without system prompt
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    response = provider.generate_response(messages, max_tokens=100, temperature=0.7)
    assert response.content
    
    # Test multi-turn conversation
    messages = [
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "4"},
        {"role": "user", "content": "What about 3+3?"}
    ]
    response = provider.generate_response(messages, max_tokens=100, temperature=0.7)
    assert response.content
```

## Common Pitfalls

### ❌ Don't: Use provider-specific config in shared code
```python
# BAD - This is provider-specific
config = {"system_instruction": system_prompt}  # Only works for some providers
```

### ✓ Do: Use messages format everywhere
```python
# GOOD - Works for all providers
messages = [{"role": "system", "content": system_prompt}]
```

### ❌ Don't: Assume all providers support system messages
```python
# BAD - Some providers might not support system role
response = provider.generate_response(messages)  # Might fail
```

### ✓ Do: Document your provider's capabilities
```python
# GOOD - Clear documentation
def supports_system_messages(self) -> bool:
    """Returns True if provider supports system role in messages."""
    return True  # or False for providers that don't
```

## Questions?

- Check existing provider implementations in `apps/credits/providers/`
- See `docs/ai-provider-refactoring-summary.md` for technical details
- Run `apps/credits/providers/test_messages_format.py` to verify your changes
