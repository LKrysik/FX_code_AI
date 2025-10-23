# Container Architecture - Dependency Injection Patterns

## 🎯 OVERVIEW

Use a central container for dependency injection to assemble application components without business logic, ensuring loose coupling and testability.

## 🏗️ PRINCIPLES

- **Pure Assembly**: Container only wires dependencies from config.
- **No Logic**: Delegate conditionals to factories.
- **Injection**: Use constructor injection exclusively.
- **Scopes**: Support singleton and transient services.

## 📜 IMPLEMENTATION

```python
class Container:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.services = {}

    def get_service(self, service_type: Type[T]) -> T:
        if service_type not in self.services:
            self.services[service_type] = self._create_service(service_type)
        return self.services[service_type]

    def _create_service(self, service_type):
        # Factory-based creation
        pass
```

## 🚫 ANTI-PATTERNS

- No global container access.
- Avoid service locator pattern.

Follow for clean, maintainable architecture.