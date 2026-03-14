---
name: No flake8 config overrides
description: Do not change flake8 max-line-length or add .flake8 / setup.cfg overrides
type: feedback
---

Do not create or modify .flake8 / setup.cfg to override max-line-length or any other flake8 rule.

**Why:** Changing the config defeats the purpose of having flake8 as a code quality tool. The rules should be respected in code, not bypassed via config.

**How to apply:** When writing new Python files, keep lines ≤ 79 characters. Break long strings, expressions, and function signatures across multiple lines instead of relaxing the limit.
