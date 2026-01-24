# Security Policy

This document outlines the security policy for the Lemello Backend repository.

---

## Reporting Security Vulnerabilities

If you discover a security vulnerability in this repository, please report it privately rather than opening a public issue.

Security issues include, but are not limited to:

- API authentication or authorization bypass
- SQL injection or other injection vulnerabilities
- Exposed credentials, API tokens, or secrets in code
- Insecure data handling or storage
- Dependency vulnerabilities with known exploits
- Infrastructure misconfigurations that impact the backend
- Session management or token validation issues
- Unsafe deserialization or input validation weaknesses

---

## Reporting Process

To report a security vulnerability:

1. Do not open a public issue or pull request
2. Contact the repository maintainers directly through private channels
3. Provide a detailed description of the vulnerability, including:
   - The affected endpoint, module, or function
   - Steps to reproduce the issue
   - Potential impact of the vulnerability
   - Any suggested remediation steps

---

## Response Timeline

Upon receiving a security report:

- Initial acknowledgment within 48 hours
- Assessment of the issue within 7 days
- Resolution and disclosure timeline determined based on severity

---

## Security Best Practices

When contributing to this repository:

- Never commit credentials, API tokens, secrets, or connection strings
- Use environment variables for all sensitive configuration
- Validate and sanitize all user inputs using Pydantic models
- Follow the principle of least privilege for database and API access
- Review dependency updates for known vulnerabilities
- Use `trufflehog` or similar tools to scan for secrets before committing
- Ensure all API endpoints enforce proper authentication and authorization

---

## Scope

This security policy applies to:

- All FastAPI application code
- API endpoints and route handlers
- Database models and queries
- Authentication and authorization logic
- Session and token management
- Dependency configurations
- Container and deployment configurations

---

## Out of Scope

Application-level security issues for other components should be reported to the appropriate repository:

- Frontend security issues: lemello-app/webapp
- Infrastructure security issues: lemello-app/infra
