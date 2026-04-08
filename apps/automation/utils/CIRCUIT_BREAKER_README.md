# Circuit Breaker Pattern Implementation

## Overview

The circuit breaker pattern prevents cascading failures when external services become unavailable. It implements three states:

- **CLOSED**: Normal operation, all requests pass through
- **OPEN**: Too many failures detected, requests fail immediately without calling external API
- **HALF_OPEN**: Testing recovery, limited requests allowed to check if service recovered

## Requirements

Implements requirements 32.3-32.4:
- Circuit breaker pattern for external API calls
- 60-second timeout before retry when circuit is open

## Architecture

### Components

1. **CircuitBreaker** (`circuit_breaker.py`)
   - Core circuit breaker implementation
   - Tracks failures and manages state transitions
   - Thread-safe with locking

2. **CircuitBreakerRegistry** (`circuit_breaker_registry.py`)
   - Manages circuit breaker instances
   - Provides pre-configured breakers for OAuth, Meta, and API Key services
   - Singleton pattern for shared state

3. **Integration with Auth Strategies**
   - OAuth Strategy: Wraps token exchange and refresh calls
   - Meta Strategy: Wraps all Meta Graph API calls
   - API Key Strategy: Wraps validation requests

## Configuration

Default circuit breaker settings:
- **failure_threshold**: 5 failures before opening circuit
- **timeout**: 60 seconds before attempting recovery
- **success_threshold**: 2 successful calls needed to close circuit

## Usage

### Getting a Circuit Breaker

```python
from apps.automation.utils.circuit_breaker_registry import CircuitBreakerRegistry

# Get OAuth circuit breaker
breaker = CircuitBreakerRegistry.get_oauth_breaker("provider_name")

# Get Meta circuit breaker
breaker = CircuitBreakerRegistry.get_meta_breaker()

# Get API Key circuit breaker
breaker = CircuitBreakerRegistry.get_api_key_breaker("service_name")
```

### Wrapping External API Calls

```python
from apps.automation.utils.circuit_breaker import CircuitBreakerOpenException

try:
    # Define the external API call as a function
    def make_api_call():
        response = httpx.post(url, data=data, timeout=30.0)
        response.raise_for_status()
        return response
    
    # Execute with circuit breaker protection
    response = breaker.call(make_api_call)
    
except CircuitBreakerOpenException as e:
    # Circuit is open, service unavailable
    logger.error(f"Circuit breaker open: {str(e)}")
    raise ValidationError("Service temporarily unavailable")
    
except httpx.HTTPStatusError as e:
    # HTTP error from external service
    logger.error(f"API call failed: {e.response.status_code}")
    raise ValidationError("API call failed")
```

## State Transitions

### CLOSED → OPEN
- Triggered when failure count reaches `failure_threshold` (default: 5)
- All subsequent requests fail immediately with `CircuitBreakerOpenException`
- No external API calls are made while open

### OPEN → HALF_OPEN
- Triggered after `timeout` seconds (default: 60)
- Allows limited requests to test if service recovered
- First failure immediately returns to OPEN state

### HALF_OPEN → CLOSED
- Triggered after `success_threshold` successful calls (default: 2)
- Circuit returns to normal operation
- Failure count is reset

## Monitoring

### Admin Endpoint

Circuit breaker status is available at:
```
GET /api/v1/admin/circuit-breakers/
```

Returns status of all circuit breakers:
```json
{
  "circuit_breakers": {
    "oauth_provider_name": {
      "name": "OAuth-provider_name",
      "state": "closed",
      "failure_count": 0,
      "success_count": 0,
      "failure_threshold": 5,
      "timeout": 60,
      "last_failure_time": null,
      "time_until_retry": 0
    }
  }
}
```

### Manual Reset

Admin users can reset all circuit breakers:
```
POST /api/v1/admin/circuit-breakers/
```

This forces all circuits to CLOSED state, useful for recovery after maintenance.

## Logging

Circuit breaker events are logged with structured context:

- **State transitions**: INFO level
  - "Circuit breaker 'name' transitioned to OPEN"
  - "Circuit breaker 'name' transitioned to HALF_OPEN"
  - "Circuit breaker 'name' transitioned to CLOSED"

- **Failures**: WARNING level
  - "Circuit breaker 'name' failure. Failure count: X/Y"

- **Open circuit**: WARNING level
  - "Circuit breaker 'name' is OPEN. Failing fast without calling external API"

## Integration Points

Circuit breakers are integrated at the following points:

### OAuth Strategy
- `complete_authentication()`: Token exchange
- `refresh_credentials()`: Token refresh

### Meta Strategy
- `complete_authentication()`: Token exchange
- `refresh_credentials()`: Token refresh
- `_fetch_business_details()`: Business account fetching (3 separate API calls)

### API Key Strategy
- `_validate_api_key()`: API key validation

## Best Practices

1. **Always wrap external API calls**: Any call to external services should use circuit breaker
2. **Use appropriate breaker**: Get the correct breaker from registry for the service type
3. **Handle CircuitBreakerOpenException**: Provide user-friendly error messages
4. **Monitor circuit state**: Use admin endpoint to track service health
5. **Log failures**: Include context about what operation failed

## Testing

Circuit breakers can be tested by:

1. Simulating failures to trigger state transitions
2. Verifying timeout behavior
3. Testing recovery in HALF_OPEN state
4. Checking thread safety with concurrent requests

## Future Enhancements

Potential improvements:
- Per-integration circuit breakers (instead of per-service-type)
- Configurable thresholds per integration type
- Metrics export for monitoring systems
- Automatic alerting on circuit open events
- Circuit breaker statistics dashboard
