# Mrliou MRL legacy indexer repair R05

origin_signature: MrLiouWord
Source / naming authority: Mr.liou / MrLiouWord
Implementation assistance: ChatGPT / Codex (OpenAI)
Rights transfer: NOT_GRANTED

Repository: `dofaromg/-Mr.liouagi`
Pinned base: `651ab1b7a03d059abb689337bb7c06f924f519f0`
Guard source: `dofaromg/flow-tasks@d43e53dee1012571915754afdfeff66c96c19615` (R03).

Fix: repair invalid YAML together with fail-closed scan/generate/upload authorization.
Backport the R03 direct-method, recursive, depth, path, revocation, smart-updater and
upload gates. Bind grants to this repository. Add an empty DENY registry; no grant
is created. Remove automatic main push and structure-content log/summary output.
Preserve the original workflow event/schedule/path section byte for byte.
The original five modified files are retained under `docs/Mrliou_MRL_Legacy_Indexer_Repair_R05_original`.

R07 review candidate, prepared for the isolated branch
`Mrliou/mrl-authorization-repair-r07`. The implementation is the tested R05
backport. R07 updates this delivery status and its manifest; code is unchanged.
Production is NOT_APPLIED until a separately reviewed merge. No main ref,
history, App permission, deployment configuration or existing route is changed
by preparing this candidate. Remote PR status belongs in the R07 repair ledger.
Existing branch/PR workflows may run under their unchanged trigger rules.

Run: `python -m unittest discover -s tests -p test_Mrliou_structure_authorization.py -v`
Tests use disposable synthetic repositories, never Mother content. Python 3.10+,
standard library only; offline YAML validation additionally uses PyYAML.

The manifest lists the exact payload, SHA-256, sizes and dependencies. Its own
bytes are excluded from its internal payload hash to avoid self-reference.
Before application, verify the exact repository/base and all original blobs.
Apply on a new isolated review branch only; validate CI there before considering
any separately authorized protected merge. Rollback by reverting the candidate
commit; do not rewrite history. Historical artifact download/use remains OPEN.
