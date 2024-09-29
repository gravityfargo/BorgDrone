    -

## Development

### Requirements

#### Manjaro Linux

```bash
pamac install \
    python-poetry \
    python-poetry-dynamic-versioning \
    pnpm \
    dart-sass

poetry config virtualenvs.in-project true
```

### Standards

views: - no direct logging, ResponseHelper() and SomeManager() only - No direct calls to any manager other than those owned by the module

#### Module.ObjectManager

- may only call `logger.debug("", color="")`
- other than database queries, all functions must return `BorgwebEvent[Object]()`
  - use `return_success()`, `return_error()`, `return_debug_success()`, `return_debug_error()` only
- In the event that the function returns any result from `BorgRunner`,
  it need's its `event` attribute changed must be returned to the view.
  - Comments should be used to indicate possible errors from `BorgRunner`.
- Error handling for `BorgRunner` should be done here, not in `BorgRunner`.

#### Module.models

- `__tablename__` is not required in flask_sqlalchemy but I like setting it explicitly
- Map types when possible

---
