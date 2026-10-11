from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

from amp.ledger import Ledger
from amp.storage import Storage
from adapters.notion_adapter import NotionAdapter
from adapters.github_adapter import GitHubAdapter
from mrl_blackhole import BlackHoleBuilder, NotionAPIClient, audit_conservation, fetch_snapshot


DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_SANDBOX_DIR = Path("data_sandbox")
DEFAULT_MANIFEST_PATH = Path("data/blackhole_manifest.json")


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open() as f:
        return yaml.safe_load(f)


def get_ledger(config: Dict[str, Any]) -> Ledger:
    data_dir = Path(config.get("data_dir", "data"))
    storage = Storage(data_dir)
    return Ledger(storage)


def cmd_init(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    ledger = get_ledger(config)
    ledger.init(reset=args.reset)
    print(f"Ledger initialized at {ledger.storage.data_dir}")


def cmd_append(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    ledger = get_ledger(config)
    entry = ledger.append(args.content)
    print(json.dumps(entry.to_dict(), indent=2, ensure_ascii=False))


def cmd_snapshot(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    ledger = get_ledger(config)
    snap = ledger.snapshot(args.name)
    print(json.dumps(snap, indent=2, ensure_ascii=False))


def cmd_verify(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    ledger = get_ledger(config)
    ok, msg = ledger.verify()
    if ok:
        print(msg)
    else:
        print(msg, file=sys.stderr)
        sys.exit(1)


def cmd_log(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    ledger = get_ledger(config)
    entries = ledger.log(args.n)
    print(json.dumps(entries, indent=2, ensure_ascii=False))


def cmd_sandbox_compare(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    ledger = get_ledger(config)

    sandbox_dir = Path(args.sandbox_dir or config.get("sandbox_data_dir", DEFAULT_SANDBOX_DIR))
    sandbox_storage = Storage(sandbox_dir)
    sandbox_ledger = Ledger(sandbox_storage)

    ok_primary, msg_primary = ledger.verify()
    if not ok_primary:
        print(f"Primary ledger failed verification: {msg_primary}", file=sys.stderr)
        sys.exit(1)

    ok_sandbox, msg_sandbox = sandbox_ledger.verify()
    if not ok_sandbox:
        print(f"Sandbox ledger failed verification: {msg_sandbox}", file=sys.stderr)
        sys.exit(1)

    ok_compare, msg_compare = ledger.compare_with_storage(sandbox_storage)
    if ok_compare:
        print(msg_compare)
    else:
        print(msg_compare, file=sys.stderr)
        sys.exit(1)


def cmd_notion_sync(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    ledger = get_ledger(config)
    entries = ledger.log(args.n)
    notion_cfg = config.get("notion", {})
    adapter = NotionAdapter(ledger.storage.data_dir)
    export_path = adapter.sync_entries(entries, notion_cfg)
    print(f"Synced {len(entries)} entries to Notion (export at {export_path})")


def cmd_github_export(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    ledger = get_ledger(config)
    entries = ledger.log(args.n)
    adapter = GitHubAdapter(ledger.storage.data_dir)
    path = adapter.export(entries)
    print(f"Exported {len(entries)} entries to {path}")


def get_blackhole_builder(config: Dict[str, Any], with_client: bool) -> BlackHoleBuilder:
    blackhole_cfg = config.get("blackhole", {}) or {}
    manifest_path = Path(blackhole_cfg.get("manifest_path", DEFAULT_MANIFEST_PATH))
    client = NotionAPIClient() if with_client else None
    return BlackHoleBuilder(client=client, manifest_path=manifest_path)


def resolve_parent_page(config: Dict[str, Any], override: str | None) -> str:
    blackhole_cfg = config.get("blackhole", {}) or {}
    parent = override or blackhole_cfg.get("parent_page_id") or config.get("notion", {}).get("root_page_id")
    if not parent:
        raise SystemExit(
            "A parent page id is required: pass --parent-page or set blackhole.parent_page_id in the config"
        )
    return parent


def cmd_blackhole_plan(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    builder = get_blackhole_builder(config, with_client=False)
    plan = builder.plan(resolve_parent_page(config, args.parent_page))
    rendered = json.dumps(plan, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
        print(f"Black hole plan written to {args.out}")
    else:
        print(rendered)


def cmd_blackhole_build(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    builder = get_blackhole_builder(config, with_client=True)
    manifest = builder.build(resolve_parent_page(config, args.parent_page))
    created = manifest.get("created") or []
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Black hole ready: created {len(created)} new object(s)")


def cmd_blackhole_snapshot(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    builder = get_blackhole_builder(config, with_client=True)
    manifest = builder.load_manifest()
    if not manifest:
        raise SystemExit("No manifest found: run blackhole-build first")

    snapshot = fetch_snapshot(builder.client, manifest)
    rendered = json.dumps(snapshot, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
        print(
            f"Snapshot written to {args.out}: "
            f"{len(snapshot['captured'])} captured, {len(snapshot['radiated'])} radiated"
        )
    else:
        print(rendered)


def cmd_blackhole_audit(args: argparse.Namespace) -> None:
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    report = audit_conservation(
        snapshot.get("captured", []),
        snapshot.get("radiated", []),
        overdue_hours=args.overdue_hours,
    )
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    print(report.summary())
    if not report.conserved:
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AMP Index-only ledger CLI")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file (default: config.yaml)",
    )
    subparsers = parser.add_subparsers(dest="command")

    p_init = subparsers.add_parser("init", help="Initialize the ledger")
    p_init.add_argument("--reset", action="store_true", help="Reset the ledger before initializing")
    p_init.set_defaults(func=cmd_init)

    p_append = subparsers.add_parser("append", help="Append a new entry")
    p_append.add_argument("content", help="Content to append")
    p_append.set_defaults(func=cmd_append)

    p_snapshot = subparsers.add_parser("snapshot", help="Create a named snapshot")
    p_snapshot.add_argument("name", help="Snapshot name")
    p_snapshot.set_defaults(func=cmd_snapshot)

    p_verify = subparsers.add_parser("verify", help="Verify chain integrity")
    p_verify.set_defaults(func=cmd_verify)

    p_log = subparsers.add_parser("log", help="Show ledger log")
    p_log.add_argument("--n", type=int, default=10, help="Number of entries to show (0 for all)")
    p_log.set_defaults(func=cmd_log)

    p_notion = subparsers.add_parser("notion-sync", help="Sync entries to Notion (best effort)")
    p_notion.add_argument("--n", type=int, default=20, help="Number of entries to sync")
    p_notion.set_defaults(func=cmd_notion_sync)

    p_github = subparsers.add_parser("github-export", help="Export entries to GitHub adapter")
    p_github.add_argument("--n", type=int, default=20)
    p_github.set_defaults(func=cmd_github_export)

    p_sandbox = subparsers.add_parser(
        "sandbox-compare",
        help="Compare primary ledger with a sandbox copy to validate lifecycle growth",
    )
    p_sandbox.add_argument(
        "--sandbox-dir",
        type=Path,
        help="Sandbox data directory (defaults to config.sandbox_data_dir or data_sandbox)",
    )
    p_sandbox.set_defaults(func=cmd_sandbox_compare)

    p_bh_plan = subparsers.add_parser(
        "blackhole-plan",
        help="Preview the MRL black hole structure without calling Notion",
    )
    p_bh_plan.add_argument("--parent-page", help="Notion page id that will host the black hole")
    p_bh_plan.add_argument("--out", type=Path, help="Write the plan to a file instead of stdout")
    p_bh_plan.set_defaults(func=cmd_blackhole_plan)

    p_bh_build = subparsers.add_parser(
        "blackhole-build",
        help="Create the MRL black hole structure in Notion (idempotent)",
    )
    p_bh_build.add_argument("--parent-page", help="Notion page id that will host the black hole")
    p_bh_build.set_defaults(func=cmd_blackhole_build)

    p_bh_snapshot = subparsers.add_parser(
        "blackhole-snapshot",
        help="Export the live black hole contents for auditing",
    )
    p_bh_snapshot.add_argument("--out", type=Path, help="Write the snapshot to a file instead of stdout")
    p_bh_snapshot.set_defaults(func=cmd_blackhole_snapshot)

    p_bh_audit = subparsers.add_parser(
        "blackhole-audit",
        help="Verify that every captured object came back out",
    )
    p_bh_audit.add_argument("snapshot", type=Path, help="JSON snapshot with captured/radiated entries")
    p_bh_audit.add_argument(
        "--overdue-hours",
        type=int,
        default=72,
        help="Hours an object may stay inside before it counts as swallowed (default: 72)",
    )
    p_bh_audit.set_defaults(func=cmd_blackhole_audit)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
