---
title: MRL structure delivery integrity repair
description: 'Reconcile the neural script receipt and account for repair sources and generated outputs.'
origin_signature: MrLiouWord
canonical_authority: Mr.liou
---

# MRL structure delivery integrity repair — 2026-10-21

origin_signature: MrLiouWord
canonical_authority: Mr.liou

## Reproduced failure and scope

Pinned repository: dofaromg/MRL_ASI_system; main/source commit: `89ad82d13452c2eb9a487e104c2eab4fcca1d31e`.
[Failed run 39530963291](https://github.com/dofaromg/MRL_ASI_system/actions/runs/39530963291), job 118996484060, 2026-10-21 10:04 Asia/Taipei: 47 tests, one failure at tests/test_Mrliou_structure_authorization.py:507; actual script 11813 bytes versus receipt 6289. Local replay reproduced the identical 47-test/one-failure result before editing.

All 19 payload files, 20 expected paths (including the manifest), and all dependency paths were inspected. Exactly one payload entry was stale; all other 18 size/hash receipts match. The two external repository dependencies package.json/package-lock.json exist and are nonempty. This is receipt drift, not evidence of an authorization-grant failure. No changes are made to dofaromg/mrlioudb.

## Original Git content and authorization lineage

| Script source commit | Bytes | SHA-256 | Source |
|---|---:|---|---|
| `886be1058d969a5ddbf86036cee7d71424ecfb2c` | 6289 | `b1220ef8ee5c21540345c3a4839243b5c788f91bbcf56054df157b189d4067bb` | Original receipt matches these exact bytes |
| `1a4b01c513e032ef7d46c4e3c0fe90c5de3ecb38` | 10756 | `c3f184f51a244a9b7914222f7624703ad996051c54fe21e072c6773314ac6021` | PR #15 actual-target lineage repair |
| `7efa7b9abb4658e2ddd1d9c3638f39874d179105` | 11813 | `f8e0e2c282f8cae4e5104c2442a96a2c3460b6e51a97386ce95eb6fad8874467` | PR #16 history-identity/classification repair; identical to pinned main |

Read the actual original/current script and both Git patches, not just their summaries. PR #15 replaces invented main-parent relationships with paginated GitHub PR base/head/merge evidence, distinguishes actual merges from test merge SHAs and main containment, and archives prior observations without restoring stale inferred edges. PR #16 uses original head refs for fork/deleted-head classification and validates SHA-256 snapshot identities, rejecting malformed/conflicting historical entries before writes. Existing legacy-history behavior remains available. These modifications do not issue scan grants or change the authorization registry.

[PR #15](https://github.com/dofaromg/MRL_ASI_system/pull/15) was merged by `dofaromg` at 2026-10-17T18:21:42Z, merge `d16872f594b62b896d57fedc7bc2830cf8961ac9`.
[PR #16](https://github.com/dofaromg/MRL_ASI_system/pull/16) was merged by `dofaromg` at 2026-10-19T10:46:59Z, merge `61e2b9451016a2d22025dd63984eac1c210ac564` (parent of pinned main).
This establishes owner-merged repository authorization for retaining the code; it is not a claim of a cryptographic author signature or a runtime scan grant. The current user instruction authorizes this receipt repair and review PR.

Original manifest remains recoverable byte-for-byte at the pinned source commit and blob `1a113d21f14f906f8261c781436769a1c2ec08ba`:
[immutable original manifest](https://github.com/dofaromg/MRL_ASI_system/blob/89ad82d13452c2eb9a487e104c2eab4fcca1d31e/config/Mrliou_Structure_Authorization_Delivery_v1.json).
The original repository/base_commit/revision/status/review_branch fields describe inherited delivery provenance and are retained verbatim. New integrity_revision records this repository, pinned source, old receipt and owner-merged source commits separately; it does not reinterpret the inherited fields as current merge/deployment status.

## Minimal repair and validation

Only the script's size_bytes and sha256 payload fields change. Add canonical_authority and append integrity_revision metadata without replacing old lineage. Runtime code, registry, original tests, trigger policy and original payload membership/dependency tree remain byte-identical.

Extend the existing read-only MRL Neural Lineage Regression workflow to run the unchanged 47-test authorization suite when delivery paths change. Both jobs explicitly check out the PR head SHA (or github.sha for push/dispatch), disable persisted credentials and retain contents:read. This workflow neither scans the real tree nor generates/uploads an index. The original structure-indexer workflow remains unchanged. The 22 existing lineage tests remain enabled.

Local verification: Python 3.12.14, 47/47 passed; Node 24.19.0, 22/22 passed, zero skipped. Every source file used for these checks was fetched at the pinned commit and checked against its Git blob SHA (39 files total). This is a targeted source checkout, not a claimed full repository build. The referenced scripts/fix-line-endings.sh is absent in the actual main tree; invocation reports missing file. All three delivered files independently checked LF. No repository-wide Next build or deployment is claimed. Exact-head remote CI/readback receipts belong in the PR after publication.

## Expected delivery and dependencies

Expected repair-source list / package map (three repair-source files; no ZIP requested):

1. config/Mrliou_Structure_Authorization_Delivery_v1.json — corrected receipt and appended lineage.
2. .github/workflows/mrl-neural-lineage.yml — read-only head verification, unchanged lineage suite plus authorization suite.
3. docs/mrl-structure-delivery-integrity-20261021.md — this audit, source evidence, file map and validation limits.

Dependency tree: owner-merged Git script -> measured byte receipt -> unchanged DeliveryContractTests; registry + scanner/generator/updater -> synthetic authorization tests; pinned original neural snapshots + generator/renderer -> existing lineage tests; existing read-only CI -> both suites. All original manifest dependencies remain present. The audit and CI are repair-support files, not substituted for original payload content. No new executable dependency is introduced.

Repair-source-only accounting: Missing=0, unaccounted Extra=0, Mismatch=0, Renamed=0, Orphan=0, Coverage=100% (3/3 planned repair files); original delivery 20/20 paths and 19/19 receipts match after repair. Remote publication and latest-head CI must be verified separately. No automatic merge or deployment.

## Measured current delivery payload and external dependencies

Manifest intentionally excludes its own recursive hash. Its final hash and this audit hash are reported in the PR receipt.

| Path | Bytes | SHA-256 |
|---|---:|---|
| `.copilot/Mrliou_structure_authorization.py` | 8783 | `e173ad61acf34d52a2c136a3cd051ebe9b777ae0fcc86a165a10e4362f4e9fff` |
| `.copilot/generator/emoji_indexer.py` | 13232 | `1f21aaa09ec2a023656b7d7c5d12dc31595129ec87ce8014e8f19a98a2643eae` |
| `.copilot/scanner/structure_scanner.py` | 13817 | `02782ba71c70a4ee3cc19cf42ef2604ff0e75992d4dd4bb88fac4bd0050ec44b` |
| `.copilot/triggers/smart_updater.py` | 11788 | `fbb183067d4549d27710e5232bb602a9457a27a83b0557ca1e0d99eb5e808d45` |
| `.github/workflows/runner-version-check.yml` | 2087 | `6688c4529847b801389138bb3c0cb9918c4db2f94c9796a31798b5fc726ea34f` |
| `.github/workflows/structure-indexer.yml` | 7135 | `f49beb89ae2faaef7f12e4c0231ccb123eacf1f293fef746adce03f0c6c5eaad` |
| `config/MRL_AUTHORIZATION_REGISTRY_v1.json` | 1113 | `7b2395fc9d95a0c0615fb93d070873461b1ce27bd32b7ea98b1ba9f61003762e` |
| `docs/Mrliou_MRL_Legacy_Indexer_Repair_R05_original/.copilot/generator/emoji_indexer.py` | 11755 | `c1365fa9a77b6788bd9f1295e94fa57b2c0965a54151af3ea53026cdcae03a6b` |
| `docs/Mrliou_MRL_Legacy_Indexer_Repair_R05_original/.copilot/scanner/structure_scanner.py` | 12348 | `ddcb95017d4028c3fa5c562d75834af0fb0fa17fca6fffc37c860f4c0ff41ab2` |
| `docs/Mrliou_MRL_Legacy_Indexer_Repair_R05_original/.copilot/triggers/smart_updater.py` | 10533 | `90882fbb3a71af7c993d3b8c0d8fa6a582c756164ddac3c602700979f15af730` |
| `docs/Mrliou_MRL_Legacy_Indexer_Repair_R05_original/.github/workflows/structure-indexer.yml` | 6253 | `97306c99b2420367d9415a4844f8ac6a0b432d9f0e51eb6b3176fa74b551453e` |
| `docs/Mrliou_MRL_Legacy_Indexer_Repair_R05_original/run_structure_index.py` | 3752 | `81c92efbcf996864ab20d27f36245f0b2f4f199fcf25792c4201ff307125925d` |
| `run_structure_index.py` | 3957 | `1d61fbd570124d87ed3df81b5467d5d85fee30245d3f312beacc2c866f7e5106` |
| `tests/test_Mrliou_structure_authorization.py` | 29254 | `3886926f2786cbfe6b584f16a5db0e43b5fdd31fb42062466f6a489bb018243b` |
| `.github/workflows/blank.yml` | 2636 | `d6ea74d155e130f0b226fcbf6111470638f737aecf7fd496615285997395009b` |
| `docs/Mrliou_MRL_Legacy_Indexer_Repair_R05.md` | 3540 | `7f07ed4ace9124953ba41189a954dc3ab7e9a001e512c788fb0d708e6b9c3efd` |
| `scripts/update-neural-map.js` | 11813 | `f8e0e2c282f8cae4e5104c2442a96a2c3460b6e51a97386ce95eb6fad8874467` |
| `tests/Mrliou_neural_history.test.cjs` | 2920 | `b102b9868e2d1f5d76539a8873ee104cd8a484804622526cdc1185e8e9833ca1` |
| `requirements.txt` | 92 | `77363d263482d45f0c94c348dada0020caac4ac6fd0ac5a200c12d30c7bc9097` |
| `package-lock.json` (external dependency) | 358790 | `53592a9273718f566d7672c0b3448fb278a7516829f96b65a47884e3d35ee071` |
| `package.json` (external dependency) | 1037 | `80a317aa171c8c6cb91c5cc859292705076247679fc533a283df69ff32cd788c` |

## Generated-output accounting and review reconciliation

The PR contains five changed paths: the three repair-source paths above plus the two existing bot-generated outputs below. The 3/3 count applies only to planned repair sources, not to the complete PR. The full path inventory is 5/5; generated outputs are attributed to Neural Branch Sync rather than described as unexpected extras.

The following immutable snapshot was independently read at `ae1efffed2cbf7248392df56959215cfb207c3df`. Later generator revisions must carry their own observed commit and hashes; these historical measurements must not be silently reassigned to a newer head.

| Generated output | Bytes | SHA-256 |
|---|---:|---|
| neural-links/branch-map.json | 469462 | a398a56c56bdf7e778cd1d686bef3071ab4d1f3455890caaf015ff00616ed0c2 |
| neural-links/synaptic-graph.mermaid | 4609 | b4b24ec74de48b1edba9858592f27650d51ba97ee3368481978e269bda574c5e |

Git commit metadata confirms that `ae1efffed2cbf7248392df56959215cfb207c3df` has the sole parent `7eb29aefa118f5286188139f046e1b1bf0aed8e7`, which is also the graph's declared source_commit. The source is therefore retained in the actual reviewed branch ancestry. The separate review reference to `05f7f12...` does not describe that parent relationship and must not be used to declare this retained lineage broken. No commit, original snapshot or source identity is removed to resolve the review.

The successful remote regression run 39557104894 checked out repair source `7eb29ae...`: authorization 47/47 and lineage 22/22. Those results are not assigned to a later bot head. The exact amended head requires a fresh remote run; a skipped or missing check remains pending even when a parent was tested. Local source checks do not replace that remote result or a main merge/deployment receipt.
