# Security Policy

## Threat model

Open Deck for MSFS is designed for a **trusted local network** (home Wi-Fi,
an isolated cockpit segment, an air-gapped machine). By default:

- HTTP and WebSocket run **without TLS** (the password protects login but does
  not encrypt traffic);
- the auto-discovery UDP beacon is unsigned — any host on the network can
  impersonate the gateway;
- the client trusts the files served by the host (the SHA-256 check protects
  only the donation block and UI integrity, not server authenticity).

**Do not expose the gateway to the internet** and do not run it on networks that
contain untrusted devices. For guest networks, use a separate VLAN or
add your own reverse proxy with authentication.

## What is already in place

- **optional password login**: PBKDF2 hash (210,000 iterations) in
  `config/auth.json`, sessions with a 12-hour TTL, `HttpOnly` cookie,
  `SameSite=Lax`, Bearer for native clients, a limit of 5 attempts per minute,
  one-time QR tokens valid for 10 minutes (accepted only via `/?pair=`);
- integrity verification of critical files (SHA-256) at host startup and in the
  browser. This is a barrier against accidental/intentional edits, not
  cryptographic protection: the manifest can be recomputed with the `--write`
  command;
- CSP `default-src 'self'`, external resources disallowed;
- request body size limit, profile and command validation;
- CORS disabled: a third-party page cannot read API responses;
- `Origin` check for browser POST/PUT and WebSocket: a foreign Origin
  receives `403` (clients without Origin are allowed);
- `Host` check against a list of local names and IPs — protection against DNS
  rebinding; an unknown Host receives `403`;
- without authentication, only the login page, `/api/health`,
  `/api/integrity`, and `/api/donation` remain (license requirements). If no
  password is set, the gateway prints a warning to the console;
- Android: WebView navigation allow-list, only `http(s)` links in the donation
  block, file/content access disabled.

## Reporting a vulnerability

Please **do not open a public issue**. Use a private channel:

- GitHub → Security → **Report a vulnerability** (Security Advisories), or
- email to `security@example.invalid` (replace with a real address before
  publishing).

Include the version, reproduction steps, and expected/actual behavior. We will
respond within 7 days.

## Supported versions

| Version | Support |
| --- | --- |
| 0.1.x | yes |

## Project support

- Author: Viktor Krasnikov — [github.com/meferspb/open-deck](https://github.com/meferspb/open-deck)
- Donation: [https://taps.uz/open_deck_fs](https://taps.uz/open_deck_fs)
