# Implementation Decisions and Deviations

**Purpose:** Record only findings that matter to approved contracts, the resulting proposal, approval and implementation evidence. Existing architecture decisions remain in `docs/HLD.md` ADR-01–ADR-20. This file does **not** overwrite them.

## Rules

- Codex may **propose**, never unilaterally approve, architecture deviations.
- A deviation needs an ID, impacted HLD/LLD/acceptance items, alternatives, rationale, user approval evidence, and follow-up tickets.
- Until approved, mark `PROPOSED` and **stop affected work**. Approved alternatives update HLD/LLD only with the user's permission.
- Implementation-specific facts that do not change architecture (e.g. pinned patch version after an expected spike) can be `VERIFIED IMPLEMENTATION CHOICE`, with real command/source evidence.
- Never use this log to declare missing mandatory features optional.

## Clarifications and verification findings

| ID | State | Observation | Consequence |
|---|---|---|---|
| CL-001 | IMPLEMENTED — approved wording correction | Assignment PDF p.4 requires **at least three** upstreams. User approved the correction on 2026-10-14 in the T-001 authorization. | LLD A04 and INDEX now say at least three, with three in-cluster baseline servers and an optional fourth remote server. ADR-09 is unchanged. |
| CL-002 | UNVERIFIED | HLD/LLD SDK v2 API examples are part of the planned contract, not runtime proof. | T-002 must test exact pinned SDK/API and real clients. Escalate if APIs differ materially. |
| CL-003 | UNVERIFIED | Actual model/provider tool calling, WooCommerce OAuth1 internal HTTP, Helm cross-namespace lifecycle and policy enforcement have not been tested. | Relevant spike/test tickets produce evidence; do not assume success. |
| CL-004 | REVIEWED LOCALLY | Original eight-page assignment PDF was available and reviewed on 2026-10-14. | Exact local filename is ignored; PDF and extracted text are excluded from staging. See [T-001 review](T-001-REVIEW.md) for requirement mapping, not a copy of the private source. |
| CL-005 | UNVERIFIED — provenance | No separate approved package or source archive was available in the repository for comparison. | Imported-document byte-for-byte provenance remains unverified. Pre-edit hashes verified only that unrelated imported files were preserved; they do not establish approval provenance. |
| CL-006 | UNVERIFIED — deadline | PDF p.1 says two weeks and gives no dated cutoff. INDEX and T-034 had asserted 2026-10-26 23:59 IST without source evidence. | Under the 2026-10-14 authorization, keep October 26 as the planning target and mark exact submission time unverified in INDEX/T-034. Obtain the authoritative invitation before submission. |
| CL-007 | OBSERVED — acceptance evidence detail | PDF p.3 explicitly requires disabled tools to disappear from both chat and the external client. LLD A14 and DEMO Step 5 summarize discovery and stale calls without explicitly naming both consumers. | Existing shared gateway architecture supports this requirement. T-029/T-031 must verify both consumer paths; no architecture or ticket expansion implemented in T-001. |
| CL-008 | OBSERVED — stronger approved baseline | PDF p.6 lists encrypted upstream credentials and additional network/SSRF hardening as stand-outs; approved HLD/LLD adopt several of these as baseline controls. | Preserve the stronger approved controls. Actual VPS deployment, fine-grained tool ACLs and multi-store remain optional; VPS deployability and private Woo MCP enforcement remain mandatory. |

## T-001 verification adjustment

The first staged `git diff --cached --check` failed on imported Markdown trailing spaces (including standard two-space hard line breaks). Added `.gitattributes` with `*.md whitespace=-blank-at-eol` to preserve imported document bytes rather than rewrite the package. This affects only Markdown end-of-line whitespace; other Git whitespace checks remain enabled. It is a repository-formatting adjustment, not an architectural deviation. README and PNG are unchanged.

## Decision proposal template

```text
ID: DEV-YYYYMMDD-001
Status: PROPOSED | APPROVED | REJECTED | IMPLEMENTED
Owner:
Ticket(s):
Conflicting approved source/sections:
Observed fact + reproducible evidence:
Options (including do nothing):
Minimal proposed change:
Mandatory acceptance impact:
Risks and rollback:
User approval reference + date:  # blank until explicitly approved
New/updated tests:
Implementation commit + verification:  # blank until executed
```
