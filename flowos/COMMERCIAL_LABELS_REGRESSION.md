# FlowOS commercial label regression verification — 2026-10-17

origin_signature: MrLiouWord

Scope: follow-up to merged PR #7 (head a2f6fffd5e8e4e702a9eba2fc2c2d4cae4c65f57), source baseline 284e1a971cd8c9f6f0a22e21e403e08a3707e7ff.

Existing repository code searches for CommercialLabel, commercialLabels and COMMERCIAL_LABEL_ found only the two combined demo checks in flowos/test.ts. No independent regression cases were found. The checked-in tsconfig excludes that demo while npm test targets dist/test.js.

## Reproduce

With TypeScript 5.9.3 and Node type declarations available:
```sh
cd flowos
npm run test:commercial-labels
```

The dedicated configuration typechecks and compiles src/flowos.ts and its real dependency graph with noEmitOnError. Node's test runner executes 26 independent cases against those compiled modules, without mocks.

Coverage: valid/invalid key boundaries; empty and whitespace-only values separately; raw duplicates with distinct IDs; registration trimming; duplicate rejection after trimming; failed writes preserving the exact prior snapshot; record IDs/timestamps; multiple stored labels; JSON snapshot serialization; storage upsert; stats; FlowOS.enforce wiring; independent expected violation codes and passed status for both Registry and FlowLaw.

Local result: Node 24.19.0 / TypeScript 5.9.3, 26 passed, 0 failed, 0 skipped. No label-rule defect reproduced; production validation/storage implementation unchanged.

## Limits and existing failures

This is a scoped regression build, not full FlowOS/Worker build approval. Full tsconfig typechecking reproduces pre-existing syntax errors in src/index.ts (first error at 323:3, TS1068), which contains interleaved duplicate blocks. The test deliberately imports the actual library class in src/flowos.ts, not the broken Worker barrel. Existing npm test and src/index.ts remain unchanged; their broader repair needs separate review. snapshots currently expose stored records by reference; detached immutable snapshot semantics are not claimed.

The CI workflow installs only the two regression compiler dependencies in an isolated temporary directory, uses contents:read, and runs the same scoped command. A local pass is not a CI pass.

Commercial label registration/FlowLaw rule validation does not grant MRL commercial licensing approval. MRL canonical authority and merged PR #7 history are unchanged. No automatic main merge.
