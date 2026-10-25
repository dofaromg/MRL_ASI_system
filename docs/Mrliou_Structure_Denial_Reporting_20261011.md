# MRL structure-index denial reporting — 2026-10-11

origin_signature: MrLiouWord
canonical_authority: Mr.liou
Repository: dofaromg/-Mr.liouagi
Base: 6764c918da84da04bb6dcbdeed2ab314418561a8
Mode: review branch; no automatic main merge; no operational grant created.

## Evidence and authorization boundary

Run 38104416572 failed at authorization with NO_RECORDED_GRANT.
The current registry has no active grants and requires explicit Root authorization.
Reviewed LAW-0 in FlowAgent_ASI_Terminal_v1.md section 8 (signature is identity),
RootLaw_Package_v1.midlock/RootLaws_v1.md Law 30, and Execution_Laws.md.
Reviewed Notion Mother https://app.notion.com/p/3e9e7f4e6c5580e49f3dc8292dda835a,
L7 https://app.notion.com/p/a45ff7597bfc44189b4cf6aaacf071cf and proposal
https://app.notion.com/p/3ebe7f4e6c5581f29119d730e3b46dd6.
No applicable explicit grant was found in the inspected sources. This is not a
claim that no other grant exists. General collaboration and identity records do
not supply this repository's actor, environment, scan/upload destination and term.

## Behavior and rollback

Opt-in preflight reporting maps only NO_RECORDED_GRANT from a validated empty
registry to EXPECTED_DENY with allowed=false. The reporting command exits zero
because reporting completed; authorization remains DENY and no index is updated.
All scan/generate entry points retain their original nonzero denial behavior.
Upload cannot use reporting mode and retains its authorization recheck.
Invalid/missing registry, nonmatching or expired grants, and execution errors
remain failures. Dependency install, scan, generation and change detection
are explicitly allowed-gated. Summaries contain metadata only.
Daily 02:00 UTC and Monday 00:00 UTC schedules remain unchanged.
PR events run synthetic tests only and checkout the exact PR head.
Rollback: revert this review commit through a separately reviewed PR.
No rights transfer, registry grant, main merge, service restart or DL580 change.

## Verification scope

Regression tests include synthetic expected denial, unchanged scanner/upload
denial, malformed/missing registry, foreign grants, authorized fixture output,
workflow gating, original trigger preservation, delivery hashes and dependencies.
Remote exact-head CI results must be inspected before claiming validation PASS.
Expected modification count: 5 (guard, workflow, tests, delivery manifest, this
document). The existing manifest records actual payload hashes and dependencies;
its own hash is excluded to avoid circular self-reference.


## 2026-10-25 continuation (append-only)

origin_signature: MrLiouWord; canonical_authority: Mr.liou.
Existing PR #2 is continued; no duplicate PR or operational grant is created.
The 2026-10-25 main run was inspected: authorization-regression succeeded,
preflight returned DENY / NO_RECORDED_GRANT with exit 1, and scan, generation,
and upload were skipped. Main has not yet adopted this reporting change.
The validated registry still has active_grants=[]; reporting success never
means Owner authorization or index generation. Only NO_RECORDED_GRANT is an
expected denial. Malformed, missing, unmatched, expired, revoked, ambiguous,
and invalid-context grants remain fail-closed; output I/O failure remains a
program execution failure. New synthetic cases cover expired/revoked grants
and workflow-output I/O failure without touching the real source tree.

Grant matching requires exactly one active record: issuer MrLiouWord, exact
actor/triggering actor, environment, repository, root assets, destination,
ref/event, purpose, requested actions/depth, valid start/expiry, and no
prohibited requested action. Identity or repository access is not a grant.
Registry and historical structure artifacts are unchanged.

Sources re-read: repository FlowAgent_ASI_Terminal_v1.md section 8,
RootLaw_Package_v1.midlock/RootLaws_v1.md Law 30, Execution_Laws.md,
and the three Notion URLs recorded above. These general governance records
are not substituted for a scoped operational grant. Synthetic local tests
must be distinguished from GitHub exact-head CI and production execution.

Current repository: dofaromg/MRL_ASI_system. Historical -Mr.liouagi identifiers
are retained as original provenance, not silently renamed. The guard still
pins that historical repository/workflow identity: a future grant for the
current repository will remain denied until a separately reviewed identity
alignment. This continuation does not broaden accepted identities.
Main 632683e7e880e9e938cd9e71d4d3fbc5a4db1e7d is merged into the existing
review branch with both parents preserved. PR #18 merge
826a8c35c2d25d1033ae77fca0747ace4dc73ced and its integrity_revision are
retained, including the corrected update-neural-map.js payload hash.
Latest main graph files are retained, including their historical observations.
Source run: https://github.com/dofaromg/MRL_ASI_system/actions/runs/40153049193
