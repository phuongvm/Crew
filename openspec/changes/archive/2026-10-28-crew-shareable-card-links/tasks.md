# Tasks: Shareable Ticket Link & In-App Crew Detail Navigation (`crew-shareable-card-links`)

- [x] **1.1 Add `card_md_link` and update `_banner_open` & `_text_md` to emit `[<id>](<dashboard>/crew?card=<id>)`** (Commit `17f9a7b`, `7b069d8`)
  - **Proof**: `python -m unittest tests/test_crew_card.py tests/test_crew_notify.py tests/test_crew_watch.py tests/test_crew_intake_create.py tests/test_crew_versions.py`
- [x] **2.1 Implement `cardFromHref`, `openCardRoute` bus, and capture-phase click interception in `ui/src/`** (Commit `1507553`, `7b069d8`)
  - **Proof**: `node ui/build.mjs --check && python -m unittest tests/test_crew_graph_serve_shell.py`
- [x] **3.1 Update `host.navigate` in `apps/desktop/src/sdk/index.ts` to open/reveal `asTile: true` route tiles** (Commit `089365ea630` in `oss/hermes-agent`)
  - **Proof**: `npx --prefix O:/workspaces/oss/hermes-agent/apps/desktop vitest run src/app/chat/sidebar/navigation.test.tsx`
- [x] **4.1 Sync compiled Crew plugin to runtime `$HERMES_HOME/plugins/crew` & skills and verify full suite** (Verified on `t_b1a531b5`, Round-3 APPROVED)
  - **Proof**: `python -m unittest tests/test_crew_card.py tests/test_crew_notify.py tests/test_crew_watch.py tests/test_crew_intake_create.py tests/test_crew_graph_serve_shell.py && node ui/build.mjs --check`
