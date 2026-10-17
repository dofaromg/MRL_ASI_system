# FlowOS Worker entry repair — 2026-10-18 (Asia/Taipei)

origin_signature: MrLiouWord

## Scope and source lineage

Continue PR #8 at `2197fc1004a9d7597df9d3d001a96bce666f540e`, preserving its commercial-service repair (`f46d095b5647acbf4f90e92e89482e2762004b73`). No merge to main, deployment, production credential access, ledger access or customer acceptance is included.

GitHub path history for `flowos/src/index.ts` contains the initial import `bcc47e49a0985b467caa60b8e1e47b0fb62b2fc7` (2026-07-03) and `0b6e8f42808362217c11bd2c1558869e6b2f46a7` (2026-10-17). Reading both versions proves byte-for-byte equality after removing the latter's single CommercialLabelRegistry export. Thus the interleaving exists in the initial repository import; the available history does not establish how that pre-import source was assembled. The commercial-label change did not introduce it. Before repair, full typecheck reproduced TS1068 at 323:3 and subsequent parser failures.

Direct Git transport was unavailable in the work environment. Files and history were read through the authorized GitHub connector; the remote repair commit uses the existing remote head as its parent and existing remote tree as its base. The local verification snapshot is not substituted for remote ancestry.

## Source ownership and retained behavior

Line references below refer to the input head's index.ts, not the repaired file.

| Original blocks | Existing owner / repair |
|---|---|
| Imports, Env and first complete fetch (1–162) | Keep one Worker entry, both auth key forms, public paths, gate forwarding, sync error statuses and defensive commit route. Deduplicate imports and VCS construction. Use namespace.get(id), already present in the second Worker copy, rather than the nonexistent id.getStub(). |
| First complete VCS/R2/persona adapters, json, safeJson (164–209) and repeats later | Keep one copy. Await adapter promises within the existing catch boundary so asynchronous failures become the intended 503 response. |
| Interleaved FlowOS declarations (243–322), createContext, snapshot, enforce and emitSignal fragments | Existing `src/flowos.ts` remains the single class owner and retains all current storage, particles, registries, tools, commercial labels, law and statistics. Restore the unique config, gate, neuralLink and emitSignal functionality there, exporting NeuralSignalResult. Use the existing storage-backed ParticleStore constructor; do not copy the broken zero-argument construction. |
| Multiple incomplete VersionControl copies and the complete later copy | Keep one complete class, syncToGitHub, init, add, commit and status. Retain development logging with a safe typeof process guard. Pre-existing VCS stubs remain explicitly marked as such; this repair does not implement KV persistence. |
| Repeated Memory/Persona/Auth support declarations | Keep one complete set. Preserve wake/list response shapes and existing stub responsibilities. |
| Duplicate local HTTP/runtime declarations | Retain minimal cloud binding contracts once, and use native HTTP Request/Response types. NeuralLink's partial Response declaration is removed so internal forwarding returns a full Response contract. No suppressions, any casts, ts-ignore or reduced strictness. |
| Final public exports | Preserve types, utils, config, gate, neural_link, adapters, FlowOS, defensive client, VCS handler and CommercialLabelRegistry. |

No unknown functional block was discarded. Consolidated copies remain in Git ancestry. No MRL names or original source signatures were renamed or remapped. Gate-before-master-key ordering, pulse-header behavior and existing VCS/persona/auth limitations are preserved; passing routing tests does not turn those existing limitations into a complete commercial authorization system.

## Build and test wiring

- tsconfig includes all src files and the existing root test.ts. `noEmitOnError` prevents failed builds from producing a misleading successful artifact; declaration output now exists.
- Package main/types match `dist/src/index.js` and `dist/src/index.d.ts`; root test.ts produces `dist/test.js`.
- npm test builds first, executes the original smoke test, then all 30 Worker/FlowOS integration, 26 commercial-label and 44 commercial-service tests. Original smoke failures now fail the process.
- Existing commercial CI retains its triggers and read-only permissions. It checks out the event's exact head SHA, runs full typecheck/npm test, builds a Worker bundle with Wrangler dry-run, then runs six workerd tests with ephemeral local KV/R2. No publish command is added.
- Toolchain: TypeScript 5.9.3; CI Node 24, @types/node 24.10.0, Wrangler 4.92.0, Miniflare 4.20260515.0. Local verification Node 24.19.0/@types/node 25.9.5; CI separately verifies its pinned types.
- AGENTS.md requests scripts/fix-line-endings.sh; repository tree has no such file. Changed text files were checked directly for LF endings. No unrelated resource README generation applies to this runtime repair.

## Local evidence and limits

After removing both generated output directories, full typecheck and npm test succeed: original smoke + 100 tests, zero failed/skipped. Wrangler 4.92.0 dry-run succeeds (54.15 KiB bundle at verification); no bindings are configured in the original wrangler.toml. Six bundled-Worker tests pass in local workerd: heartbeat, unauthorized/authorized VCS init, R2 list, persona wake, defensive commit without external sync. The first ad-hoc emulator invocation used an incorrect modulesRoot and failed startup; setting modulesRoot to the bundle directory resolved that harness path error and the committed test includes it explicitly.

Synthetic bindings and mocked GitHub requests do not prove production KV/R2/DO provisioning or GitHub token permissions. Node route tests cover namespace.get(id) forwarding and GitHub success/HTTP/network failures. Existing commercial tests continue to cover loopback HTTP, temporary ledgers, recovery and account isolation.

Full compilation: local PASS. Worker bundle/local runtime: local PASS. Remote exact-head CI must be checked after publication and is not asserted by this source file. Worker deployment and DL580 commercial-service/customer-node acceptance: NOT VERIFIED.

Existing Neural Branch Sync can append a skip-ci bot commit; its two neural-links files must be distinguished from this repair and any latest-head CI gap reported explicitly. Existing unrelated Kubernetes CI failures must not be presented as FlowOS compilation failures or silently changed in this repair.

## Delivery audit

Expected file list = the nine implementation/test/CI files below plus this audit file (10 actual source files). Dependency tree: Worker → NeuralLink / VCS handler / route adapters; FlowOS → original storage/particles/registries/law + config/gate/neuralLink; npm test → full build → smoke + Worker routes + commercial tests; CI → exact source head → full checks → Wrangler bundle → local workerd tests.

Package map: Git tree changes only these ten paths; all other existing tree entries remain inherited. No ZIP requested or produced. Generated dist, node_modules, test ledgers and temporary bundles are not delivery files. Existing service/provisioner and commercial regression source files remain unchanged.

Expected vs generated paths: Missing=0, Extra=0, Mismatch=0, Renamed=0, Orphan=0, Coverage=100% at local source verification. Files are nonempty actual implementation/tests, with no new placeholder substituting for functionality. Pre-existing marked stubs are preserved as described above. Remote read-back is required before final DELIVERY_PASS.

| File | Bytes | SHA-256 |
|---|---:|---|
| `.github/workflows/flowos-commercial-labels.yml` | 1646 | `030670a5dc3d4a38dfed48796d49738dbfa011f0927cac5dd4ba3fc68bfd9324` |
| `flowos/package.json` | 890 | `07d47b3575d091e69e8ee30e6d510d854ce7df9d9877a3c73d46462941a60181` |
| `flowos/src/core/neural_link.ts` | 3656 | `535607b1e89d63a546e04ac144263a3587ec5f080d7b3a78a6a91c8f8c97f3cb` |
| `flowos/src/flowos.ts` | 4323 | `3c52ea5c1072903a2d75addfd13a0f30ee3b164d48e3d80eb910fa0dbd87e61d` |
| `flowos/src/index.ts` | 10908 | `3a2b735feec945431815e2659d06a7a2f4ace79b93d2ce624c82ff7b2bda6522` |
| `flowos/test.ts` | 3420 | `25fe03eb9d8e291c838c06df1bc49fb713467dc89057031adbaa12325aa08bd2` |
| `flowos/tsconfig.json` | 533 | `93958a6d80732eb0f341dd9ed3287416670301b812aeef474d75c84fc42bb576` |
| `flowos/tests/worker-routes.test.cjs` | 8803 | `ff6e43c19391b6a2a5bdd90d82599d180cc7f6689d62e0b1162e30919aa79092` |
| `flowos/tests/worker-runtime.test.cjs` | 1918 | `6e6e0ff0c53423116f18406241614d1344e750d6a00eaa9cffacca1f28ab176e` |

This audit's own byte size and SHA-256 are recorded in the PR delivery evidence to avoid a self-referential digest. Remote CI run URL and observed exact head are recorded there after publication.
