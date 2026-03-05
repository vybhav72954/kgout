# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 1.0.x   | ✅         |

## Security Considerations

**kgout exposes files over the network.** When using the `local` destination, kgout starts an HTTP server and creates a public ngrok tunnel. Anyone with the tunnel URL can browse and download files from the watched directory. Be aware of what files exist in your watch directory.

### Recommendations

- Only use kgout in ephemeral environments like Kaggle notebooks
- Do not point `watch_dir` at directories containing credentials, keys, or personal data
- Use ngrok's authenticated tunnels (paid plan) if you need access control
- When using Google Drive, use a service account with minimal scopes (`drive.file` only)
- Never commit service account JSON keys to git — use Kaggle Secrets or environment variables

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately:

1. **Do NOT open a public GitHub issue**
2. Email: [your-email@example.com] with subject "kgout security"
3. Include: description, reproduction steps, and impact assessment
4. You will receive a response within 48 hours

We will coordinate disclosure and credit reporters in the changelog.
