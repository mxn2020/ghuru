# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in gh-agent-funhouse, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities.
2. Email the maintainers with details of the vulnerability.
3. Include steps to reproduce the issue if possible.
4. Allow reasonable time for the issue to be addressed before public disclosure.

## Security Design

### Token Storage

- **Primary**: System keyring (via the `keyring` library) for OS-native credential storage.
- **Fallback**: Fernet-encrypted local file with a machine-specific key stored with restricted file permissions (0o600).
- Tokens are **never** printed to stdout/stderr or included in log output.

### GitHub API Communication

- All API calls use HTTPS.
- Rate limiting is handled with exponential backoff.
- Error messages redact authentication tokens.

### Required GitHub App Permissions

If using the Device Flow OAuth with a GitHub App, the following permissions are required:

| Permission       | Access     | Purpose                                      |
| ---------------- | ---------- | -------------------------------------------- |
| `repo`           | Read/Write | Create repos, branches, files, PRs           |
| `issues`         | Read/Write | Create and manage mission task issues         |
| `actions`        | Read/Write | Trigger and monitor workflow runs             |
| `pull_requests`  | Read/Write | Create PRs from bootstrap and agent runs      |
| `metadata`       | Read       | Basic repository information                  |

### Personal Access Token Scopes

If using a PAT, the following scopes are required:

- `repo` (full control of private repositories)
- `workflow` (update GitHub Action workflows)

## GitHub Enterprise

gh-agent-funhouse is designed for GitHub.com. GitHub Enterprise Server support is not yet tested. The base API URL is currently hardcoded to `https://api.github.com`. Enterprise support may be added in a future release by making the base URL configurable.
