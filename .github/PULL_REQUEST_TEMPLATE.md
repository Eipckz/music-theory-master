## What & why

<!-- What does this change, and what problem does it solve? -->

## Checklist

- [ ] `python -m pytest tests -q` passes locally
- [ ] No new network calls at runtime (test_netsafety still passes)
- [ ] New Qt slots wear `@guard(...)`; heavy imports stay lazy
- [ ] New settings added to `_SCHEMA` with default + type
- [ ] New exercise types registered (auto-covered by the parametrized suite) with teaching text, and a lesson if they back a new skill
