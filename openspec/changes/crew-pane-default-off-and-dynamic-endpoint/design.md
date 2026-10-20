# Design: Crew Desktop Pane Default OFF & Dynamic Dashboard Endpoint Detection

## 1. Architectural Overview

```
                      ┌────────────────────────────┐
                      │    ui/src/desktop.tsx      │
                      │  data.defaultCollapsed     │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │    desktop/plugin.js       │
                      │ (Recompiled via build.mjs) │
                      └─────────────┬──────────────┘
                                    │
                        Hermes Desktop Pane Shell
                                    │
                                    ▼
                       Pane Arrives Collapsed (Rail)

─────────────────────────────────────────────────────────────────

                      ┌────────────────────────────┐
                      │     ui/src/host.ts         │
                      │   resolveDashboardBase()   │
                      └─────────────┬──────────────┘
                                    │
            ┌───────────────────────┴───────────────────────┐
            │                                               │
            ▼                                               ▼
┌───────────────────────────────┐       ┌───────────────────────────────┐
│     Hermes Web Dashboard      │       │        Hermes Desktop         │
│ window.location.origin        │       │ window.hermesDesktop          │
│ + /plugins/crew               │       │ .getConnection().baseUrl      │
└───────────────┬───────────────┘       └───────────────┬───────────────┘
                │                                       │
                └───────────────────────┬───────────────┘
                                        │
                                        ▼
                      ┌────────────────────────────┐
                      │   Board & Card Components  │
                      │  Dynamic Top-Right Link    │
                      └────────────────────────────┘
```

## 2. Component Design Details

### 2.1 FlowPane Registration (`ui/src/desktop.tsx`)
In `ui/src/desktop.tsx`:
```tsx
      {
        id: 'flow',
        area: PANES_AREA,
        title: 'Crew flow',
        data: { placement: 'right', width: '260px', hideOnly: true, collapsible: true, defaultCollapsed: true },
        render: () => <Pane api={api} />
      }
```
Setting `defaultCollapsed: true` tells `apps/desktop/src/components/pane-shell/tree/store.ts` (`adoptMissingPanes`) to immediately invoke `setPaneCollapsed('flow', true)` when the pane first enters the layout tree.

### 2.2 Endpoint Resolution Helper (`ui/src/host.ts` / `ui/src/components/boardUtil.ts`)
Create a pure resolution helper `resolveDashboardUrl(boardUrl?: string)`:
1. If running in a browser environment (`typeof window !== 'undefined' && window.location?.origin`):
   - If `window.location.origin` is not `null` and not `file://`:
     - Check if `boardUrl` is a dummy loopback (e.g. `http://127.0.0.1:8799` or `http://localhost:8799`).
     - If dummy loopback or absent: Use `window.location.origin + (hosted ? '/plugins/crew' : '/')`.
     - If `boardUrl` is an explicit public domain/tailnet URL (not loopback 8799): Use `boardUrl`.
2. In Hermes Desktop context:
   - Check `(window as any).hermesDesktop?.getConnection()`: If remote baseUrl is present, format `${baseUrl}/plugins/crew`.
   - Fall back gracefully to `boardUrl || '/'`.

### 2.3 Backend Fallback (`scripts/crew_card.py`)
In `scripts/crew_card.py:dashboard_url()`:
- Check `~/.hermes/config.yaml` for `dashboard.public_url`.
- If present, return `public_url`.
- Otherwise fallback to loopback port.

## 3. Negative Impact Analysis (3 Worst-Case Scenarios)
1. **Scenario 1**: `defaultCollapsed: true` permanently prevents a user from opening the pane.
   - *Mitigation*: In Hermes Desktop layout tree, `defaultCollapsed` only seeds initial arrival state; user expansion persists in `localStorage` / `$layoutTree` atoms and is never overruled on subsequent boots.
2. **Scenario 2**: In headless or unit test environments, `window.location` is undefined or lacks `origin`.
   - *Mitigation*: All helpers guard with `typeof window !== 'undefined' && window.location?.origin` with fallback to `boardUrl || '/'`.
3. **Scenario 3**: `ui/build.mjs` outputs mismatched bundles or exceeds Desktop bundle size cap (512 KiB).
   - *Mitigation*: Run `node ui/build.mjs --check` in the verification suite, which byte-checks both bundles and enforces Desktop size constraints.
