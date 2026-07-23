from purgatory import AsyncCircuitBreakerFactory

circuit_breaker = AsyncCircuitBreakerFactory(default_threshold=5, default_ttl=30)

