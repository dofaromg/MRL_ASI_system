# MRL Neural Branch Sync merge lineage repair

origin_signature: MrLiouWord
canonical_authority: Mr.liou

The former generator assigned every PR target to main, including PR #9, whose actual target is `Mrliou/flowos-commercial-labels-regression-20261017` (PR #8). It also restored stale edges from historical snapshots into the effective graph.

The existing `scripts/update-neural-map.js` now reads the complete paginated GitHub PR collection through `gh api`. REST `base.ref` / `head.ref` correspond to baseRefName / headRefName. It preserves PR number, title, author login, source URL, base/head repositories and SHAs, original creation/update/merge timestamps, and actual merge commit. An open PR's synthetic test merge SHA is deliberately not classified as a real merge. Original raw values are retained in the pinned source fixture. Missing API evidence aborts before file replacement. Forks, deleted heads, repeated branch names and multiple PRs per branch are handled separately.

`parent` means the observed PR target, not an assertion of Git branch creation ancestry. Multiple targets use `parents`, with singular `parent: null`; branches without PR evidence receive no fabricated parent. Synapses retain the existing base-to-head display convention and explicitly record the PR and commit evidence. Each merged PR is independently checked for merge-commit ancestry in `origin/main`: confirmed / not_in_main / unknown. Open or closed-unmerged PRs are not_established. A squash/rebase of a later target branch may omit the original nested merge SHA; the graph conservatively reports commit containment, not semantic code equivalence. Deployment always remains not_verified; this generator does not obtain deployment evidence.

## Original observations and precedence

The complete main graph at `284e1a971cd8c9f6f0a22e21e403e08a3707e7ff` (updated 2026-10-17T11:47:23.671Z) and the graph at `0bf3a9f9eff42c49b87985997bde7195795a242b` (14:41 UTC) remain in the corrected graph's `history`. The latter is also retained as a standalone original snapshot in `neural-links/history/`. Existing commit history and author attribution are unchanged.

History entries preserve full snapshot payloads, including original timestamps, node and edge metadata, and any authors or source SHAs already present. They receive SHA-256 identifiers and are deduplicated without recursively copying history. Missing historical nodes remain as unknown historical nodes. Legacy relationships remain inside historical observations, never in schema v2 effective synapses. Thus an old erroneous main-to-PR9 edge cannot overwrite fresh PR metadata. API failure does not downgrade confirmed information to invented main relationships.

The pinned PR metadata and commit-ancestry responses used for the initial corrected graph are in `tests/fixtures/`. PR #9 merge SHA `f022d69e41e8c415cc955a226ff84b64313060e2` is not an ancestor of main `284e1a971cd8c9f6f0a22e21e403e08a3707e7ff`; PR #8 was OPEN at observation. PR #7 directly merged main and its merge SHA equals that main commit. Original PR #9 author login is dofaromg, PR #7 author login is Copilot; these are recorded as source metadata, not reassigned.

## Validation and operation

Run `node --test tests/Mrliou_neural_history.test.cjs tests/mrl-neural-lineage.test.cjs` (17 passing tests locally, Node 24.19.0). This covers the requested stacked merge, unmerged PR #8, direct main merge, nested containment, original metadata, complete pagination, API failure, fork collisions, closed/unmerged PRs, missing commits, deduplicated history and reproducible graph generation. Existing four history tests remain unchanged.

A read-only GitHub Actions workflow runs the same suite on push and pull_request. Existing Neural Branch Sync also runs the suite before generation. Its unsupported `merged` activity was replaced with supported `closed`, `reopened` and `edited` activities so target changes are observed. Ordinary regeneration remains `node scripts/update-neural-map.js` then `node scripts/generate-mermaid.js`, with authenticated gh and fetched Git refs. No main merge or deployment is performed by this repair.

Repository-wide `npm run build` was attempted but unavailable in the partial API checkout (`next: not found`). The repository's AGENTS.md line-ending command was attempted; `scripts/fix-line-endings.sh` does not exist at the pinned source commit. All delivery text files are separately checked for LF. Neither unavailable check is reported as passed.

## Expected_File_List

1. scripts/update-neural-map.js
2. .github/workflows/neural-sync.yml
3. .github/workflows/mrl-neural-lineage.yml
4. tests/mrl-neural-lineage.test.cjs
5. tests/fixtures/mrl-neural-prs-20261017.json
6. tests/fixtures/mrl-neural-ancestry-20261017.json
7. neural-links/history/0bf3a9f9eff42c49b87985997bde7195795a242b.branch-map.json
8. neural-links/branch-map.json
9. neural-links/synaptic-graph.mermaid
10. docs/mrl-neural-lineage-20261018.md
11. docs/mrl-neural-lineage-audit-20261018.json

Expected_Dependency_Tree / package map: GitHub PR observations + git merge-commit containment → existing generator → effective branch-map + archived history → existing Mermaid generator → synaptic-graph. The regression suite consumes both pinned source fixtures and original snapshot; both CI workflows consume that suite. Audit JSON records sizes and SHA-256 for the ten payload files (it excludes its own hash to avoid self-reference). No ZIP is requested or substituted for source files. Additional unrelated source files are not part of this delivery.
