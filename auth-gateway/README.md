# Paper GitHub App login gateway (deployment candidate)

Status: **gateway and dedicated-host UI tested locally, not deployed**. The public GitHub Pages site retains its existing local-first sync behavior. No real user has signed in through this gateway, and no private checkpoint has been confirmed by this prototype.

## Purpose and boundary

The user should sign in once on a new device, then let Paper Lab reconnect and rotate its short-lived GitHub App user token without typing a PAT or carrying a private entry file. The gateway keeps the GitHub App client secret on the server. Its browser controller persists only the rotating refresh credential as AES-GCM ciphertext with a non-extractable device key; access tokens remain in the existing `PaperSync` page memory. The device database must stay out of Paper backups and private sync payloads.

**Deploy the Paper site and gateway under one dedicated HTTPS origin.** Do not enable this on `1337816143.github.io`: its project paths share an origin and browser storage, so another page under that account would have the same browser origin. `checkedConfig` rejects a GitHub Pages origin. A dedicated origin also makes popup `postMessage` and refresh `Origin` checks meaningful. The public GitHub Pages version can remain as a learning mirror while the dedicated host is assessed.

Changing origins does **not** move existing local notes. Before switching, the current device must export and import its existing Paper backup or complete a verified private sync checkpoint on the old origin. The gateway cannot recreate notes that were never uploaded. A same-origin script injection on the dedicated host could still act with the browser's credential; the host must serve only reviewed Paper assets and use a restrictive content security policy.

## External setup required before activation

1. Register a GitHub App owned by the user's account, with expiring user access tokens enabled. Install it for **only** `1337816143/My-Evolution`. Grant repository **Contents: read/write** and the default Metadata read permission; do not grant Actions, Administration or all-repository access. Restrict the app's callback URL to `<dedicated-origin>/callback`.
2. Provision a private HTTPS web service for this gateway and the Paper site at the same origin. Build Paper into `dist/site` using `python scripts/build.py`; set `PAPER_SITE_DIR` to that absolute directory and start `node auth-gateway/server.mjs`. Keep `GITHUB_APP_CLIENT_SECRET` and a random 32-byte `COOKIE_KEY_BASE64URL` in the service's secret store, never in GitHub Pages, source files, URLs, logs or screenshots. Configure `GITHUB_APP_CLIENT_ID`, `PUBLIC_BASE_URL` and `PAPER_SITE_ORIGIN` with that exact origin. The gateway serves only files under `PAPER_SITE_DIR` and applies a script CSP to HTML.
3. The dedicated-host build loads `oauth-ui.mjs` and its encrypted browser controller; the public GitHub Pages build skips login activation. Verify the login button, refresh recovery, and `PaperSync`'s private repository write/readback before claiming `云端已确认`. Test an isolated synthetic note on two devices and verify refresh-token rotation, revocation, offline edits and conflict preservation. The UI uses a same-origin Web Lock so only one Paper tab holds rotating credentials at a time. Other tabs remain local and take over automatically after the active tab closes; check “云端已确认” on the active tab before clearing any local data. Browsers without Web Locks keep private sync disabled.

The GitHub App registration and service creation expand access to a private repository and need review of the exact permission screen. No credentials should be sent in chat.

## Local verification

```text
cd auth-gateway
npm test
```

The tests mock GitHub's token and repository APIs and check state/PKCE binding, wrong-account rejection, exact-origin refresh, popup origin/source/nonce validation and token storage order. A separate Chrome browser check confirmed that the IndexedDB key is non-extractable and that encrypted refresh data survives reload. These checks do not replace a real GitHub App authorization and two-device private sync test.

## Security decisions

- The OAuth state and PKCE verifier are encrypted in a short-lived `HttpOnly; Secure; SameSite=Lax` cookie in the popup. Tokens never appear in a redirect URL.
- The callback verifies the expected GitHub login and private repository visibility before posting tokens to the opener at an exact origin. The browser also checks popup identity and nonce.
- The `/refresh` endpoint accepts only the dedicated origin, a bounded JSON body and a rotating GitHub refresh credential. GitHub App token expiration must be enabled; revoked or expired access requires a fresh login.
- The gateway never writes user notes. `PaperSync` remains responsible for repository privacy checks, its dedicated data branch, merge conflict handling and confirmed GitHub write/readback.
- A production reverse proxy should cap request rates and body sizes and keep access logs free of authorization data. The gateway's bounded JSON parser is an application safeguard, not a complete denial-of-service control.
