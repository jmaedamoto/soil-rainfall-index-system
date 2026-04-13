## Promotion Checklist

- [ ] This PR promotes changes from `develop` / `refactor` to `staging` or `main`
- [ ] `SOIL_RAINFALL_ROUTE_PROFILE=production` was used for verification
- [ ] Only production client routes are exposed
- [ ] Development or test-only routes are not exposed
- [ ] `test_*.py`, `server/tests/`, `.pytest_cache/`, `__pycache__/`, and `*.pyc` are not included in the release payload
- [ ] Deployment config for the target environment fixes `SOIL_RAINFALL_ROUTE_PROFILE=production`

## Route Profile

- Target profile: `production`

## Verification

- Route check:
- File cleanup check:
- Additional validation:

## Notes

- Promotion-specific risks:
- Follow-up tasks:
