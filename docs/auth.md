# Authentication

gh-agent-funhouse supports two authentication methods: GitHub App Device Flow OAuth and Personal Access Tokens.

## Device Flow OAuth (Recommended)

The Device Flow is ideal for CLI tools because it works without a web server callback:

```
┌─────────┐          ┌──────────┐          ┌──────────┐
│  ghfun   │──POST──▶│  GitHub   │          │  Browser │
│  CLI     │◀─code───│  /device  │          │          │
│          │         │  /code    │          │          │
│  Shows   │         └──────────┘          │          │
│  code to │                                │          │
│  user    │─────── user enters code ──────▶│ github   │
│          │                                │ .com/    │
│  Polls   │──POST──▶┌──────────┐          │ login/   │
│  for     │◀─token──│  GitHub   │          │ device   │
│  token   │         │  /oauth   │          └──────────┘
└─────────┘         └──────────┘
```

### Setup

1. **Create a GitHub App** at https://github.com/settings/apps/new:
   - Set a name (e.g., "my-ghfun-app")
   - Enable "Device Flow" under OAuth settings
   - Set required permissions:
     - Repository: Read & Write
     - Issues: Read & Write
     - Actions: Read & Write
     - Pull Requests: Read & Write
     - Metadata: Read
   - Note the **Client ID**

2. **Login**:

```bash
ghfun auth login --device-flow --client-id YOUR_CLIENT_ID
```

3. Follow the on-screen instructions to enter the code in your browser.

## Personal Access Token (Fallback)

For simpler setups, use a PAT:

### Via Environment Variable

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
ghfun auth login
```

### Via Command Line

```bash
ghfun auth login --pat ghp_xxxxxxxxxxxxx
```

### Via Interactive Prompt

```bash
ghfun auth login
# You'll be prompted to enter your token
```

### Required PAT Scopes

- `repo` - Full control of private repositories
- `workflow` - Update GitHub Actions workflows

## Token Storage

Tokens are stored securely using a two-tier approach:

1. **System Keyring** (preferred): Uses OS-native credential storage via the `keyring` library.
   - macOS: Keychain
   - Linux: Secret Service (GNOME Keyring, KDE Wallet)
   - Windows: Windows Credential Manager

2. **Encrypted File** (fallback): If keyring is unavailable, tokens are encrypted using Fernet symmetric encryption. The encryption key is stored in a file with restricted permissions (0600) in the application config directory.

!!! warning
    The encrypted file fallback is less secure than the system keyring. A warning is displayed when this fallback is used.

## Status & Logout

```bash
# Check authentication status
ghfun auth status

# Remove stored credentials
ghfun auth logout
```

## GitHub Enterprise

GitHub Enterprise Server is not yet supported. The API base URL is currently hardcoded to `https://api.github.com`. Enterprise support is planned for a future release.
