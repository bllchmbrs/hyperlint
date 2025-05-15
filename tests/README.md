# hyperlint Tests

This directory contains tests for the hyperlint project.

## Current Test Coverage

The current test suite covers the following components:

| Component | Coverage | Status |
|-----------|----------|--------|
| BaseEditor | 84% | ✅ Good |
| AIEditor | 81% | ✅ Good |
| CustomRuleEditor | 91% | ✅ Excellent |
| FolderProcessor | 76% | ✅ Good |
| CLI | 73% | ✅ Good |
| ArbitraryLinkEditor | 32% | ❌ Needs improvement |
| ImageAdditionEditor | 20% | ❌ Needs improvement |
| LinkEditor | 31% | ❌ Needs improvement |
| ValeEditor | 39% | ❌ Needs improvement |
| Utils | 17% | ❌ Needs improvement |

Overall coverage: 53%

## Test Structure

- `tests/test_folder_processor.py` - Tests for folder processing functionality
- `tests/unit/` - Unit tests for individual components
  - `tests/unit/editors/` - Tests for editor implementations
  - `tests/unit/test_cli.py` - Tests for CLI commands

## Running Tests

To run all tests:
```bash
pytest
```

To run tests with coverage:
```bash
pytest --cov=hyperlint tests/
```
ptest
To generate a coverage report:
```bash
pytest --cov=hyperlint --cov-report=html tests/
```

## Test Dependencies

Test dependencies are defined in `pyproject.toml` under `project.optional-dependencies.test`.

To install dependencies:
```bash
uv pip install -e ".[test]"
```

## Next Steps

### High Priority

1. Add tests for ArbitraryLinkEditor
2. Add tests for ImageAdditionEditor
3. Add tests for LinkEditor
4. Add tests for ValeEditor
5. Improve tests for utility functions

### Medium Priority

1. Add integration tests for complete workflows
2. Add tests for error handling and edge cases
3. Improve CLI test coverage

### Low Priority

1. Add performance tests
2. Add property-based tests with hypothesis
3. Set up CI/CD pipeline with GitHub Actions
