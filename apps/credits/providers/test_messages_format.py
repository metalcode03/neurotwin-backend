"""
Quick test script to verify messages format works across all providers.

Run with: python manage.py shell < apps/credits/providers/test_messages_format.py
"""

from apps.credits.providers.gemini import GeminiService
from apps.credits.providers.mistral import MistralService
from apps.credits.providers.cerebras import CerebrasService


def test_message_formatting():
    """Test that all providers accept messages format."""
    
    # Sample messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]
    
    print("Testing message format compatibility...\n")
    
    # Test Gemini message formatter
    print("1. Testing GeminiService._format_messages_for_gemini()")
    try:
        gemini = GeminiService()
        formatted = gemini._format_messages_for_gemini(messages)
        print(f"   ✓ Gemini formatted output:\n{formatted}\n")
    except Exception as e:
        print(f"   ✗ Gemini formatting failed: {e}\n")
    
    # Test that providers accept messages parameter
    print("2. Testing provider interfaces accept messages parameter")
    
    providers = [
        ("GeminiService", GeminiService),
        ("MistralService", MistralService),
        ("CerebrasService", CerebrasService),
    ]
    
    for name, provider_class in providers:
        try:
            provider = provider_class()
            # Check method signature
            import inspect
            sig = inspect.signature(provider.generate_response)
            params = list(sig.parameters.keys())
            
            if 'messages' in params:
                print(f"   ✓ {name}.generate_response() accepts 'messages' parameter")
            else:
                print(f"   ✗ {name}.generate_response() missing 'messages' parameter")
                print(f"     Found parameters: {params}")
        except Exception as e:
            print(f"   ✗ {name} initialization failed: {e}")
    
    print("\n3. Testing messages without system prompt")
    messages_no_system = [
        {"role": "user", "content": "Hello!"}
    ]
    
    try:
        gemini = GeminiService()
        formatted = gemini._format_messages_for_gemini(messages_no_system)
        print(f"   ✓ Gemini formatted output (no system):\n{formatted}\n")
    except Exception as e:
        print(f"   ✗ Gemini formatting failed: {e}\n")
    
    print("✓ All tests completed!")


if __name__ == "__main__":
    test_message_formatting()
