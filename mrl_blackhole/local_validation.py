# origin_signature: MrLiouWord
"""Run canonical live validation only on the authorized DL580 D: drive."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import io
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from .canonical import CanonicalAPIClient, CanonicalBlackHoleBuilder, snapshot, audit_snapshot

def validate_destination(path, platform=None, hostname=None):
    platform = platform or os.name
    hostname = hostname or socket.gethostname()
    value = PureWindowsPath(str(path))
    if platform != "nt" or hostname.upper() != "WIN-PBVUI7VK2A6":
        raise ValueError("This entrypoint must execute on the authorized DL580 host")
    if value.drive.upper() != "D:" or not value.is_absolute() or ".." in value.parts:
        raise ValueError("An absolute D: directory without traversal is required")
    if not str(value).lower().startswith("d:\\mrl_mother\\"):
        raise ValueError("Use the existing D:\\MRL_Mother tree")
    return value

def file_evidence(path):
    payload = path.read_bytes()
    return {"name": path.name, "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}

def public_summary(receipt):
    # Never print snapshots, titles, IDs of captured material, tokens or errors' response bodies.
    return {key: receipt.get(key) for key in (
        "record_id", "origin_signature", "hostname", "status", "structure_status",
        "second_preflight_operations", "captured", "radiated", "pending",
        "violation_count", "warning_count", "runtime_acceptance", "files")}

def run_validation(directory, client):
    directory.mkdir(parents=True, exist_ok=True)
    manifest = directory / "canonical_manifest.json"
    receipt = {"record_id": "MRL_BLACKHOLE_DL580_LIVE_" + directory.name,
               "origin_signature": "MrLiouWord", "canonical_authority": "Mr.liou",
               "hostname": socket.gethostname(), "started_at": datetime.now(timezone.utc).isoformat(),
               "status": "IN_PROGRESS", "files": []}
    builder = CanonicalBlackHoleBuilder(client=client, manifest_path=manifest)
    plan = builder.plan()
    (directory / "preflight.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    builder.build()
    second = builder.plan()
    receipt["second_preflight_operations"] = len(second["operations"])
    if second["operations"]:
        raise RuntimeError("Second preflight still requires structural changes")
    builder.build()
    receipt["structure_status"] = "LIVE_BUILDER_AND_REPEAT_PASS"
    current = snapshot(client, builder.load_manifest())
    snapshot_path = directory / "snapshot.json"
    snapshot_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    report = audit_snapshot(current)
    audit_path = directory / "conservation_audit.json"
    audit_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for key in ("captured", "radiated", "pending", "runtime_acceptance"):
        receipt[key] = report[key]
    receipt["violation_count"] = len(report["violations"])
    receipt["warning_count"] = len(report["warnings"])
    receipt["status"] = "PASS" if report["runtime_acceptance"] == "PASS" else "HOLD"
    receipt["completed_at"] = datetime.now(timezone.utc).isoformat()
    expected = ["preflight.json", "canonical_manifest.json", "snapshot.json", "conservation_audit.json"]
    receipt["files"] = [file_evidence(directory / name) for name in expected]
    receipt["expected_file_list"] = expected + ["live_receipt.json"]
    receipt["history_location"] = manifest.name + ".history"
    receipt["validation_scope"] = "Builder/repeat/snapshot/audit only; no fault injection, record creation, owner acknowledgement or service restart"
    receipt_path = directory / "live_receipt.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = public_summary(receipt)
    summary["files"] = receipt["files"] + [file_evidence(receipt_path)]
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation-dir", required=True)
    args = parser.parse_args()
    validate_destination(args.operation_dir)
    if not os.environ.get("NOTION_TOKEN"):
        raise SystemExit("Existing local NOTION_TOKEN is required; do not send it to the platform")
    # Retain stdout/stderr locally. Only metadata summary leaves this entrypoint.
    folder = Path(args.operation_dir)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        with (folder / "validation.log").open("x", encoding="utf-8") as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                summary = run_validation(folder, CanonicalAPIClient())
    except Exception as error:
        summary = {"origin_signature": "MrLiouWord", "status": "ERROR",
                   "error_type": type(error).__name__, "runtime_acceptance": "HOLD"}
    print(json.dumps(summary, ensure_ascii=False))
    raise SystemExit(0 if summary.get("status") == "PASS" else 2)

if __name__ == "__main__":
    main()
