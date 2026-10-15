# T-001 documentation baseline review

Date: 2026-10-14. Scope: A20 documentation foundation only. T-001 is CODE_COMPLETE pending user review, with source-package provenance explicitly UNVERIFIED. No commit, push, dependency installation, application implementation or infrastructure change.

## Source review

The locally supplied original assignment PDF was read using the bundled Python `pypdf.PdfReader`: eight pages, all extracted page text reviewed. This was a requirements/content review, not a PDF layout inspection. No private PDF or extracted text is staged. No separate approved source package was available in the repository; byte-for-byte comparison with that original package was NOT RUN. The imported files are preserved except the explicitly authorized edits listed below.

| Assignment pages | Mandatory coverage reviewed | Planned implementation/verification references |
|---|---|---|
| 1–2 | Explainable implementation; four layers; gateway-only access; same Helm charts; pre-registered Woo; admin CRUD/invites/key management; member own keys and credential isolation | HLD §§1–7; LLD §§4–6, 9–10; A05, A06, A08, A09, A19; T-022; DEMO |
| 3 | Real checkout; A creates product and retrieves real order; B external client and two-upstream prompt; next-call revocation; disable, outage and user-attributed audit | A01, A09–A16; DEMO Steps 1–8; T-031 |
| 3–4 | Local Kubernetes, same Helm templates for VPS deployability, cluster workloads, PVCs, stable Ingress, probes/resources and Secrets | A02, A17–A19; HLD §7; LLD §10 |
| 4 | Custom five-tool Woo MCP over Streamable HTTP; private access; dynamic aggregation and CRUD; collision handling; bounded failures; server-side credentials; at least three upstreams; roles, hashed keys, dashboard audit | A03–A09, A13–A18; LLD §§4–8; THREAT_MODEL |
| 5 | LLM tool loop through gateway, logged-in user attribution, tool trace, LLM secret handling | A10–A12, A16, A18; LLD §9; T-003, T-026, T-027 |
| 7–8 | Live two-user demo, internals/security explanation, local/VPS story, upgrade/rollback, repo/source/charts, README instructions, design/tradeoffs, four threat-model topics, optional-feature inventory | A20; HLD; THREAT_MODEL §§3–7; DEMO; T-030, T-032–T-034 |

No mandatory capability omission was identified in the planned coverage. This is document traceability, not implementation evidence. README setup instructions, source code, charts and demo video remain outstanding later-ticket deliverables.

## Discrepancies and approved corrections

- CL-001: PDF p.4 says at least three upstreams; corrected LLD A04 and INDEX wording. Three in-cluster baseline servers and optional fourth remote remain unchanged.
- CL-006: PDF p.1 says two weeks; no calendar cutoff appears in the eight pages. Removed unsupported `23:59 IST` claims from INDEX and T-034. October 26 remains a planning target, not a PDF-verified deadline.
- CL-007: disable evidence must cover both chat and external-client discovery, as explicitly required on p.3. Recorded for later acceptance testing; no architectural change made.
- CL-008: some p.6 stand-out security controls are already part of the stronger approved architecture; retained them. Actual VPS deployment is optional, deployability mandatory. Tool ACLs and multi-store are optional.
- INDEX header had six columns versus five in its rows; corrected the header without changing dependencies or ticket scope.

## Preservation and verification

Existing HEAD: `64c9aa45ee83c0500d91cff4669e72a51e8e43ec`. Only `.gitignore`, README and the PNG were tracked before T-001.

Pre-edit SHA-256:

- README: `658f7d35b354b0c6b3e81adf0bdcfebdb60a7cbafe1ad01428737f79f97573ed`
- Architecture PNG: `fd6da00ca8d48ad890750090500413eceb1f1e8465cc43f2c8f2ed012427b429`

Verification results are recorded below after running the checks. No original-package equality claim is made. No architecture deviation was approved or implemented; only the user's 2026-10-14 T-001 corrections were applied.

## Executed checks and outcomes

- `python3 /tmp/k8s-t001-baseline/verify.py`: PASS. All required documents and exactly T-001–T-034, S-001–S-005, B-001–B-003 exist; all relative Markdown link targets resolve; INDEX rows have five columns; README/PNG equal HEAD and pre-edit hashes; other imported files changed only at STATUS, DECISIONS, LLD, INDEX and T-034. Checked 21 ignored examples and 10 safe examples with `git check-ignore --no-index -q`, all passed. This temporary local harness is not a repository deliverable.
- `git ls-files README.md docs/images/kubernetes-architecture.png`: PASS; both preserved files remain tracked.
- `git diff --cached --check`: initially FAIL on imported Markdown trailing spaces; PASS after adding `.gitattributes` with `*.md whitespace=-blank-at-eol`. Imported Markdown hard breaks preserved; other whitespace checks remain active.
- `git diff --check`: PASS.
- `git check-ignore -v 'Urumi AI FDE Internship - Round 1_ MCP Gateway on Kubernetes.pdf'`: PASS; exact root PDF excluded by `.gitignore`.
- `python3 /tmp/k8s-t001-baseline/check-staged.py`: PASS. Staged inventory limited to 55 documentation/config paths, matching working files. Credential-pattern scan found no private keys, AWS/GitHub/LLM/Woo tokens, JWTs or credential-bearing URLs. The only literal-assignment candidate in an additional scan was LLD's safe `automountServiceAccountToken: false` instruction. No secret-bearing config or private source material is staged. Pattern scanning is not a guarantee against arbitrary secret formats.
- `git diff --cached --stat` and `git status --short --branch`: inspected. Final inventory: 54 added files and one modified file (`.gitignore`), all staged; no unstaged or non-ignored untracked files. README/PNG absent from diff. Private PDF and macOS metadata remain ignored.
- HEAD remains `64c9aa45ee83c0500d91cff4669e72a51e8e43ec`; no new commit. Initial staging was blocked by the sandbox's Git-index restriction; approved escalation allowed staging only.
- Original-package comparison: NOT RUN, no separate package available. Runtime/application/Helm/security integration tests: NOT RUN, out of documentation-only scope and no implementation exists.

Review adjustment beyond the original edit list: `.gitattributes` preserves existing Markdown formatting while satisfying the requested staged check. No architectural decisions changed. T-002 remains NOT_STARTED. User review and explicit commit authorization are still required.
