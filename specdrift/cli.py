from __future__ import annotations

import argparse
import json
from pathlib import Path

from specdrift.config import load_config
from specdrift.detector.report import generate_drift_report


def cmd_init(_: argparse.Namespace) -> int:
	print("SpecDrift init: TODO (interactive setup wizard)")
	print("For now, copy specdrift.yaml.example → specdrift.yaml")
	return 0


def cmd_sync(args: argparse.Namespace) -> int:
	config = load_config(Path(args.config))
	report = generate_drift_report(config)

	out = json.dumps(report, indent=2, ensure_ascii=False)
	if args.output:
		Path(args.output).write_text(out, encoding="utf-8")
		print(f"Wrote drift report → {args.output}")
	else:
		print(out)

	if args.deploy:
		print("Deploy requested: TODO (build dashboard + publish to GitHub Pages)")

	return 0


def cmd_status(args: argparse.Namespace) -> int:
	_ = load_config(Path(args.config))
	print("SpecDrift status: TODO (quick status without full sync)")
	return 0


def cmd_report(args: argparse.Namespace) -> int:
	config = load_config(Path(args.config))
	report = generate_drift_report(config)

	if args.format == "json":
		out = json.dumps(report, indent=2, ensure_ascii=False)
		if args.output:
			Path(args.output).write_text(out, encoding="utf-8")
			print(f"Wrote report → {args.output}")
		else:
			print(out)
		return 0

	raise SystemExit(f"Unsupported format: {args.format}")


def build_parser() -> argparse.ArgumentParser:
	p = argparse.ArgumentParser(prog="specdrift", description="SpecDrift CLI")
	p.add_argument(
		"--config",
		default="specdrift.yaml",
		help="Path to specdrift.yaml (default: specdrift.yaml)",
	)

	sub = p.add_subparsers(dest="cmd", required=True)

	p_init = sub.add_parser("init", help="First-time setup")
	p_init.set_defaults(fn=cmd_init)

	p_sync = sub.add_parser("sync", help="Sync sources and generate drift report")
	p_sync.add_argument("--deploy", action="store_true", help="Deploy dashboard (TODO)")
	p_sync.add_argument("--output", help="Write JSON report to file")
	p_sync.set_defaults(fn=cmd_sync)

	p_status = sub.add_parser("status", help="Check status without full sync")
	p_status.set_defaults(fn=cmd_status)

	p_report = sub.add_parser("report", help="Print drift report")
	p_report.add_argument("--format", default="json", choices=["json"])
	p_report.add_argument("--output", help="Write report to file")
	p_report.set_defaults(fn=cmd_report)

	return p


def main(argv: list[str] | None = None) -> None:
	parser = build_parser()
	args = parser.parse_args(argv)
	raise SystemExit(args.fn(args))
