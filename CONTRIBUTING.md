# Contributing to Lemello Backend

This repository contains the FastAPI backend for Lemello. Contributions must follow the guidelines below to ensure consistency, security, and reliability.

---

## Linear as Source of Truth

All work is tracked in Linear. Branch names, pull requests, and commits must reference Linear ticket IDs.

---

## Branch Naming

All feature branches must reference a Linear ticket ID:

```text
LMLO-123/short-description
```

Examples:

```text
LMLO-456/add-recipe-endpoint
LMLO-789/fix-auth-validation
```

---

## Pull Request Policy

All changes to this repository must be made through pull requests.

Direct commits to the main branch are not permitted.

---

## Pull Request Guidelines

### Keep PRs Small and Focused

- One logical change per pull request
- Backend-only changes (no frontend logic)
- Single feature, fix, or refactor per PR

### Required Information

Every pull request must include:

- Link to the Linear ticket
- Summary of changes and motivation
- API surface changes (endpoints, schemas, models)
- Database migrations or schema changes (if any)
- Manual testing performed
- Risk assessment and rollout notes

Use the pull request template when creating PRs.

---

## Before Contributing

Ensure you have the required tools installed and configured:

- Python 3.14.x
- Poetry
- PostgreSQL 16 (with pgvector for local development)
- Docker (for containerized testing)
- git

Verify your Python version:

```bash
python --version
```

Expected output:

```text
Python 3.14.x
```

---

## Python Code Hygiene

Before submitting a pull request, ensure your code passes all quality checks.

### Formatting

Format code according to the project's style standards. Use the formatting tools configured in the repository.

### Linting

Run linting checks to catch common issues and enforce code quality standards.

### Type Checking

Ensure all type hints are correct and pass type checking validation.

### Testing

Run the test suite to verify that your changes do not break existing functionality.

---

## Security Requirements

### Never Commit Secrets

- No credentials, API tokens, or connection strings in code
- Use environment variables for all sensitive configuration
- Never commit `.env` files or files containing secrets
- Use `trufflehog` or similar tools to scan for secrets before committing

### Input Validation

- All user inputs must be validated using Pydantic models
- Sanitize data before processing or storing
- Follow secure coding practices for SQL queries and API endpoints

### Dependencies

- Review dependency updates for known vulnerabilities
- Ensure all dependencies are compatible with Pydantic v2
- Keep `poetry.lock` up to date and commit changes

---

## Database Changes

If your pull request includes database schema changes:

- Provide migration scripts or instructions
- Document breaking changes clearly
- Test migrations on a local database before submitting
- Consider backward compatibility for zero-downtime deployments

---

## Commit Messages

Use clear, descriptive commit messages that reference the Linear ticket:

```text
[LMLO-123] Add recipe creation endpoint

- Implement POST /api/recipes
- Add Recipe and RecipeCreate Pydantic models
- Add database queries for recipe persistence
- Add unit tests for endpoint validation
```

Reference the Linear ticket ID in square brackets at the start of the message.

---

## Questions and Support

If you have questions about contributing:

- Review the README.md for architecture and setup details
- Check the Linear ticket for context and requirements
- Reach out to the repository maintainers for clarification

---

## License

All contributions are subject to the repository license. By submitting a pull request, you agree that your contributions will be licensed under the same terms.
