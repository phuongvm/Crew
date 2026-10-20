# Proposal: Crew Desktop Pane Default OFF & Dynamic Dashboard Endpoint Detection

## 1. Executive Summary
Configure the Crew flow pane in Hermes Desktop to be collapsed (toggled OFF) by default upon plugin registration, and eliminate the hardcoded `http://127.0.0.1:8799/` link by implementing dynamic endpoint detection across both Hermes Web Dashboard and Hermes Desktop.

## 2. Motivation
- **Issue 1 (Desktop Pane Screen Real Estate)**: The right-side `FlowPane` arrives expanded by default, encroaching 260px on the active chat surface without the user requesting it. Users prefer it minimized on the rail until explicitly opened.
- **Issue 2 (Hardcoded Loopback Link Broken Over Network)**: The top-right `link` on the Crew board hardcodes `http://127.0.0.1:8799/`. For users accessing Hermes remotely (e.g. over LAN, VPN, Tailscale, or via remote gateway), this link points to loopback on the client machine and fails with connection errors. It must dynamically detect and adapt to the current dashboard endpoint (`window.location.origin` or configured gateway public URL).
- **Issue 3 (Standalone Daemon Decommissioning)**: As confirmed with the Commander, standalone HTTP daemon on port 8799 is retired in favor of the unified React UI embedded within Hermes Desktop and Web Dashboard.

## 3. Scope of Changes
- `oss/crew/ui/src/desktop.tsx`: Add `defaultCollapsed: true` to `PANES_AREA` registration.
- `oss/crew/ui/src/components/Board.tsx`: Update top-right link to dynamically resolve from `location.origin` / gateway connection rather than blindly accepting loopback `dashboard_url`.
- `oss/crew/ui/src/components/CardPage.tsx`: Add dynamic card detail link / endpoint detection.
- `oss/crew/scripts/crew_card.py`: Update `dashboard_url()` fallback to inspect Hermes `config.yaml` (`dashboard.public_url`).
- `oss/crew/ui/build.mjs`: Rebuild `desktop/plugin.js` and `scripts/crew_dashboard/app.js`.
- `oss/crew/tests/`: Add automated unit tests verifying `defaultCollapsed: true` and dynamic URL resolution.
- Runtime sync: Synchronize updated bundles to active profile runtime plugins.

## 4. Verification Criteria
- `node ui/build.mjs --check` passes cleanly.
- Unit tests asserting `defaultCollapsed: true` pass with exit code 0.
- Unit tests asserting dynamic dashboard endpoint resolution pass with exit code 0.
- All code modifications executed in an isolated worktree under `O:/workspaces/.worktrees/crew-pane-endpoint-fix` adhering to Zero-Checkout invariant.
