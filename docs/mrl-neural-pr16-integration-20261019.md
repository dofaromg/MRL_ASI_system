# MRL Neural Branch Sync PR 16 integration repair — 2026-10-19

origin_signature: MrLiouWord
canonical_authority: Mr.liou

PR: https://github.com/dofaromg/MRL_ASI_system/pull/16

## Verified lineage and conflict source

Pinned main: `bf4569431afaf9e5b64facdddcda0d0879dbc999`.
Pinned PR 16 head: `9016d4c7cdca4e17a45889ebed4eb7cb45fe1fce`.
Common ancestor: `1fb4006252514ae74bd7f5d76c32ae060d04bf64`.
PR 15 merge: `d16872f594b62b896d57fedc7bc2830cf8961ac9`, contained in both sides.
PR 16's earlier merge `f714a351a19812595aa6af5206c1ff5bd14cb66e` has parents `7d9eb015b164de267d6fecf494b88f11614ff6b4` and the common ancestor. Main subsequently merged PR 12 as `e8375a3bc34a34b4ba664c0af48add08b1efa841` and its bot produced `bf456943...`. Both tracked trees differ ONLY in the two generated artifacts; all other original blobs agree. This permits an ordinary two-parent integration commit on PR 16, preserving all of main's other code and workflows. No force update or main merge is authorized by this repair.

`parent` means observed PR target, not branch creation ancestry. Main's PR 16 target is `main`; the earlier branch observation targets `copilot/fix-github-actions-job-failure`. The original timestamps are distinct observations, retained as such.

| Original artifact commit | source_commit | updated_at / observed_at | PR 12 | PR 15 | PR 16 |
|---|---|---|---|---|---|
| `9016d4c7...` | `fdaa7c270284f4448b232e4c7b93a2b16256e463` | `2026-10-18T18:35:22.627Z` | open; no merge | merged, main confirmed | open, old target |
| `bf456943...` | `e8375a3bc34a34b4ba664c0af48add08b1efa841` | `2026-10-18T19:01:54.229Z` | merged, main confirmed | merged, main confirmed | open, target main |

PR 9 retains target `Mrliou/flowos-commercial-labels-regression-20261017`, merge commit `f022d69e41e8c415cc955a226ff84b64313060e2`. GitHub comparison confirms this exact merge commit is NOT an ancestor of pinned main (diverged). PR 8 remains open, mergeCommit=null, main_integration=not_established. Deployment remains not_verified.

## Data preservation

No API-backed regeneration was used to resolve these conflicts. Main's effective graph, PR records, source_commit, updated_at and all observed_at values are unchanged. Mermaid is byte-identical to main. Both complete original JSON byte streams are pinned under neural-links/history/<artifact-commit>.branch-map.json. Schema-v2 history retains all ten main entries and all nine PR 16 entries verbatim; their union had ten entries. The two complete top-level observation payloads (excluding recursive history) are appended with computed SHA-256: resulting history count=12. Old inferred edges remain archived only.

## Confirmed generator repairs and current review assessment

All five retrieved inline threads were outdated at inspection, but were rechecked against the actual current source:

- Codex fork/deleted-head classification: still reproducible. Classify by original headRefName while keeping the namespaced node ID. Regression covers feature, fix and copilot prefixes for both fork and deleted heads.
- Copilot malformed history identity: still reproducible. Validate full SHA-256 against payload before insertion. Missing, empty, malformed, mismatched and recursive identities fail before file writes; conflicting duplicate metadata fails closed; original entries are never overwritten. Tests verify unchanged inputs and idempotence.
- mainContains origin/main requirement: intentional evidence boundary in current workflow (fetch-depth:0). Missing authoritative ref remains unknown; no substitution of potentially stale local main. No correctness fix required for this supported CI path.
- O(nodes * PRs) scan: performance suggestion; no observed correctness defect. Left unchanged for minimal scope.
- Prior audit count: expected_file_count=11 means ten payload entries plus the separately declared audit_file. The old receipt is pinned to payload_commit, not current blobs. This clarification is appended here; original audit bytes and historical claims are not rewritten.

Old-head check runs: GitGuardian success; Copilot full suite failure. Its job 117760338103 log ends with `Missing sub-command` from the hosted review runtime and exit 1; review says full agentic suite unavailable. This is distinct from generator test failure. Old head had no MRL Neural Lineage Regression run. Prior PR 15 success is not attributed to PR 16.

## Validation and delivery

Local Node v24.19.0: 22 passed, 0 failed, 0 skipped (17 existing + 5 new regression cases). Tests include byte hashes of both original snapshots, main effective observation preservation, history union, PR 9/15/16 lineage and Mermaid consistency.

Repository-wide npm run build cannot execute in this isolated source checkout: next is not installed; no all-build PASS claim. Required scripts/fix-line-endings.sh is absent in pinned repository tree; invocation fails, all seven delivery files independently checked LF. No dependency or workflow mutation is made to mask these limitations.

Expected_File_List: the six payload files below plus this actual audit document (seven files). No ZIP requested. Relative to pinned main, Mermaid already exists unchanged; relative to old PR 16 head, both generated files are resolved. No names were changed; all other blobs are inherited from pinned main unchanged.

| Actual payload path | Bytes | SHA-256 |
|---|---:|---|
| `scripts/update-neural-map.js` | 11813 | `f8e0e2c282f8cae4e5104c2442a96a2c3460b6e51a97386ce95eb6fad8874467` |
| `tests/mrl-neural-lineage.test.cjs` | 11359 | `c432e650e48816edc8a83bada2237413531ff481573326381ae90f84e1af9bcd` |
| `neural-links/branch-map.json` | 391669 | `05283e7dda951c9f5db99b6a277e3830e5ddf3e5fe563410623fe5ee546c9e13` |
| `neural-links/synaptic-graph.mermaid` | 4399 | `b3bcf6f7c677e5796cc9f9bbac6a50a0c3bcb4d36657e036688925bdbb6c507d` |
| `neural-links/history/bf4569431afaf9e5b64facdddcda0d0879dbc999.branch-map.json` | 314845 | `a6a9252c064ea741dbfb0461882853af1561cc7853d9ad741d3fe078b3704ea8` |
| `neural-links/history/9016d4c7cdca4e17a45889ebed4eb7cb45fe1fce.branch-map.json` | 276433 | `41969a7313cf38de657da156ea11baf72e1a06254015fdeff24f16f2092d88d9` |

Dependency tree: GitHub PR metadata + Git ancestry -> generator -> active graph; original snapshots -> validated history merge -> archived observations; graph -> unchanged Mermaid renderer -> Mermaid; existing regression workflow -> both existing test suites -> generator + pinned snapshots. Package map: existing repository tree plus these seven actual files, no dependency packages or deployment payload.

Local coverage: 7/7 present, nonempty actual files; Missing=0, Extra=0, Renamed=0, Orphan=0. Hashes above cover payload; this document's hash is reported separately in the final remote receipt to avoid recursive self-hashing. Remote readback, final commit parents, mergeability and exact-head CI must be checked after publishing; this document does not declare those pending gates PASS. No main merge or DL580 deployment performed.
