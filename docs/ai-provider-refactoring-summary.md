# AI Provider Refactoring Summary

## Overview
Standardized prompt formatting across all AI providers (Gemini, Mistral, Cerebras) to eliminate inconsistencies and provider-specific bugs.

## Problem Statement
The system had inconsistent prompt handling:
- **Gemini**: Used invalid `system_instruction` in config (caused 400 INVALID_ARGUMENT errors)
- **Mistral/Cerebras**: Used OpenAI-style messages array
- **AIService**: Passed `prompt` and `system_prompt` separately, causing provider-specific logic to leak

## Solution

### 1. Standardized Internal Format
All providers now use a unified messages array format:
```python
messages = [
    {"role": "system", "content": "System instructions"},
    {"role": "user", "content": "User prompt"}
]
```

### 2. Updated AIProvider Base Class
Changed interface from:
```python
def generate_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    ...
) -> ProviderResponse
```

To:
```python
def generate_response(
    messages: List[dict],
    max_tokens: int = 1000,
    temperature: float = 0.7
) -> ProviderResponse
```

### 3. Provider-Specific Adaptations

#### GeminiService
- **CRITICAL FIX**: Removed invalid `system_instruction` from config
- Added `_format_messages_for_gemini()` method to convert messages to single formatted string
- Format: `[SYSTEM INSTRUCTIONS]\n{content}\n\n[USER]\n{content}`

#### MistralService
- Updated to accept messages array directly
- Passes messages to API unchanged (OpenAI-compatible)

#### CerebrasService
- Updated to accept messages array directly
- Passes messages to API unchanged (OpenAI-compatible)

### 4. AIService Changes
- Builds messages array before calling providers:
```python
messages = []
if system_prompt:
    messages.append({"role": "system", "content": system_prompt})
messages.append({"role": "user", "content": prompt})
```
- Updated `_execute_with_fallback()` to pass messages instead of separate prompts

## Benefits

1. **No More Gemini Errors**: Eliminated 400 INVALID_ARGUMENT errors from invalid `system_instruction`
2. **Provider Agnostic**: AIService doesn't need provider-specific logic
3. **Scalable**: Easy to add new providers - just implement message translation
4. **Consistent**: All providers follow same interface contract
5. **Clean Architecture**: Provider-specific formatting stays in provider classes

## Files Modified

1. `apps/credits/providers/base.py` - Updated interface
2. `apps/credits/ai_service.py` - Build messages array, updated fallback logic
3. `apps/credits/providers/gemini.py` - Fixed invalid config, added message formatter
4. `apps/credits/providers/mistral.py` - Updated to use messages
5. `apps/credits/providers/cerebras.py` - Updated to use messages

## Testing Recommendations

1. Test Gemini with system prompts (should no longer error)
2. Test all providers with and without system prompts
3. Verify CSM profile integration still works
4. Test fallback logic across providers
5. Update unit tests to use new messages format

## Migration Notes

- **Breaking Change**: Provider implementations must update `generate_response()` signature
- **Backward Compatibility**: None - all providers must be updated together
- **External Impact**: None - changes are internal to provider layer
