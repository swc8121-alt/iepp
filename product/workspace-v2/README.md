# IEPP AI Workspace — goal-first UX v2 (prototype)

## Why this exists
A general customer should understand **"Organize a project, set up an AI team, and track the work"** before encountering IEPP protocol terminology. This isolated prototype reuses the earlier UI concept and changes the customer-facing onboarding. It does not change IEPP research claims or any production service.

## Included
- Korean goal-first landing page with direct text entry and three starter scenarios (content creator, solo business, research).
- Two-step guided preview: goal/project name and template → a three-role AI team plus three draft tasks.
- Demo-only project creation that updates project, agent, and task views **within the browser's in-memory state**; the plan is lost after reload.
- Clear navigation: Home / Projects / AI Team / Tasks / Records & Verification. Existing lineage and alert pages remain available.
- Explicit indication of what is **demo/example data**, not live verification or execution.
- Responsive layout and keyboard-accessible input/buttons.

## How to review
Open `IEPP_Workspace_v2_Interactive_Prototype.html` locally in a browser or serve it as a static page. Enter a goal, choose one of the three scenarios, inspect the recommended structure, and create a mock project. Open Projects / AI Team / Task Center to inspect the new draft. No credentials or API keys are required.

## What this does NOT do
- The existing public app at `iepp-lineage.swc8121.chatgpt.site` is **not modified or deployed** by this PR.
- No backend API calls, live agent execution, payment, real approval, scheduler, or user-authentication flow exists in the static HTML.
- Example agent names, task counts, timestamps, and L1 checkpoint statuses should not be interpreted as currently measured data.
- IEPP L1 is at most registry-relative event-chain consistency. No verified original-instance identity, physical hardware anchoring, clone resistance, or live cross-model continuity is claimed.

## Acceptance checks performed (local static prototype)
- Desktop 1440 × 1000: page rendered, goal entered, template selected, preview shown, draft project created, displayed counts updated, three draft tasks filtered, no observed JavaScript page errors.
- Mobile 390 × 844: page rendered, goal form visible, document did not horizontally overflow, no observed JavaScript page errors.
- Source JavaScript syntax checked with Node.js v22 `--check`.

## Integration work before launch
1. Locate and connect the actual site source/deployment pipeline; preserve production data and use a staging environment.
2. Wire the goal-first flow to authenticated `project recommendation request → save pending recommendation → user browser review`; do not silently approve or execute.
3. Provide project-scoped agent/task entities and clear status states: draft, requested, approved, running (observed), reported, stopped, verification-unknown.
4. Replace example counts with authenticated API read responses, including separate record-chain consistency and actual runtime observation indicators.
5. Add real evidence/export, storage permissions, basic billing controls, and consent/error/empty states before paid launch.
6. Conduct moderated 5–10 user onboarding tests targeting an accurate product description and a first draft project in under three minutes.

**Status:** Prototype ready for human review, *not* a production deployment.
