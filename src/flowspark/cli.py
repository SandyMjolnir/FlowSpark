"""FlowSpark command-line interface."""
from __future__ import annotations

from __future__ import annotations

import argparse
import json
import os
import sys


def _cmd_convert(args: argparse.Namespace) -> int:
    from flowspark.parser import AlteryxParser
    from flowspark.mapper import ToolMapper
    from flowspark.generator import NotebookGenerator
    from flowspark.estimator import EffortEstimator

    parser = AlteryxParser()
    try:
        workflow = parser.parse_file(args.input)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    mapper = ToolMapper()
    mapped = mapper.map_workflow(workflow)

    gen = NotebookGenerator()
    formats = args.formats.split(",") if args.formats else ["py", "ipynb", "md"]
    written = gen.generate(workflow, mapped, output_dir=args.output_dir, formats=formats)

    for fmt, path in written.items():
        print(f"Written [{fmt}]: {path}")

    if args.estimate:
        estimator = EffortEstimator()
        report = estimator.estimate(workflow, mapped)
        print()
        print(report.dashboard_text())

    if args.json_report:
        estimator = EffortEstimator()
        report = estimator.estimate(workflow, mapped)
        report_path = os.path.join(args.output_dir, f"{workflow.name}_effort.json")
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report.as_dict(), fh, indent=2)
        print(f"Written [json]: {report_path}")

    return 0


def _cmd_estimate(args: argparse.Namespace) -> int:
    from flowspark.parser import AlteryxParser
    from flowspark.mapper import ToolMapper
    from flowspark.estimator import EffortEstimator

    parser = AlteryxParser()
    try:
        workflow = parser.parse_file(args.input)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    mapper = ToolMapper()
    mapped = mapper.map_workflow(workflow)

    estimator = EffortEstimator()
    report = estimator.estimate(workflow, mapped)
    print(report.dashboard_text())
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    from flowspark.validator import ValidationFramework

    try:
        with open(args.input_data, encoding="utf-8") as fh:
            input_rows = json.load(fh)
        with open(args.output_data, encoding="utf-8") as fh:
            output_rows = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error loading data files: {exc}", file=sys.stderr)
        return 1

    keys = args.keys.split(",") if args.keys else None
    framework = ValidationFramework()
    report = framework.validate(
        workflow_name=args.name or "workflow",
        input_rows=input_rows,
        output_rows=output_rows,
        key_columns=keys,
    )
    print(report.summary())
    return 0 if report.passed else 1


def main(argv: list | None = None) -> int:
    """Entry point for the ``flowspark`` CLI."""
    cli = argparse.ArgumentParser(
        prog="flowspark",
        description="Alteryx to PySpark Migration Accelerator",
    )
    sub = cli.add_subparsers(dest="command", required=True)

    # ---- convert ----
    p_convert = sub.add_parser("convert", help="Convert an Alteryx workflow to PySpark")
    p_convert.add_argument("input", help="Path to .yxmd / .yxwz / .yxmc file")
    p_convert.add_argument(
        "-o", "--output-dir", default=".", help="Output directory (default: current)"
    )
    p_convert.add_argument(
        "--formats",
        help="Comma-separated output formats: py,ipynb,md (default: all)",
    )
    p_convert.add_argument(
        "--estimate", action="store_true", help="Print effort estimation dashboard"
    )
    p_convert.add_argument(
        "--json-report", action="store_true", help="Write JSON effort report"
    )
    p_convert.set_defaults(func=_cmd_convert)

    # ---- estimate ----
    p_estimate = sub.add_parser("estimate", help="Show effort estimation for a workflow")
    p_estimate.add_argument("input", help="Path to .yxmd / .yxwz / .yxmc file")
    p_estimate.set_defaults(func=_cmd_estimate)

    # ---- validate ----
    p_validate = sub.add_parser("validate", help="Compare input vs output datasets")
    p_validate.add_argument("input_data", help="Path to expected data JSON file")
    p_validate.add_argument("output_data", help="Path to actual data JSON file")
    p_validate.add_argument("--keys", help="Comma-separated join key columns")
    p_validate.add_argument("--name", help="Workflow name for the report")
    p_validate.set_defaults(func=_cmd_validate)

    args = cli.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
