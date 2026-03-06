"""Validation framework: compare input and output datasets to verify migration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ColumnMismatch:
    """Describes a column-level difference between two schemas."""

    column: str
    issue: str  # "missing_in_output", "missing_in_input", "type_mismatch"
    input_type: Optional[str] = None
    output_type: Optional[str] = None


@dataclass
class ValidationReport:
    """Full validation report comparing an input dataset against an output."""

    workflow_name: str
    row_count_input: int
    row_count_output: int
    column_mismatches: List[ColumnMismatch] = field(default_factory=list)
    sample_diffs: List[Dict[str, Any]] = field(default_factory=list)
    passed: bool = False
    notes: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def row_count_match(self) -> bool:
        return self.row_count_input == self.row_count_output

    @property
    def schema_match(self) -> bool:
        return len(self.column_mismatches) == 0

    def summary(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        row_match = "✅ match" if self.row_count_match else "❌ mismatch"
        schema_match = "✅ match" if self.schema_match else "❌ mismatch"
        lines = [
            f"Validation {status} – {self.workflow_name}",
            f"  Rows  : input={self.row_count_input}, output={self.row_count_output}  {row_match}",
            f"  Schema: {schema_match}",
        ]
        for cm in self.column_mismatches:
            lines.append(f"    - {cm.column}: {cm.issue} ({cm.input_type} vs {cm.output_type})")
        for note in self.notes:
            lines.append(f"  Note: {note}")
        return "\n".join(lines)


class ValidationFramework:
    """Compare input and output dataset snapshots to verify a migration.

    This implementation works with plain Python dicts / lists (no PySpark
    dependency) so it can be used in CI pipelines and unit tests without a
    Spark cluster.  When running on Databricks the caller can convert Spark
    DataFrames to :func:`to_dict` snapshots before passing them in.

    Usage::

        framework = ValidationFramework()
        input_rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        output_rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        report = framework.validate(
            workflow_name="MyWorkflow",
            input_rows=input_rows,
            output_rows=output_rows,
        )
        print(report.summary())
    """

    def validate(
        self,
        workflow_name: str,
        input_rows: List[Dict[str, Any]],
        output_rows: List[Dict[str, Any]],
        key_columns: Optional[List[str]] = None,
        tolerance: float = 0.0,
    ) -> ValidationReport:
        """Validate that *output_rows* matches *input_rows*.

        Parameters
        ----------
        workflow_name:
            Logical name used in the :class:`ValidationReport`.
        input_rows:
            List of row dicts representing the **expected** (Alteryx) output.
        output_rows:
            List of row dicts representing the **actual** (PySpark) output.
        key_columns:
            Optional list of column names to use as a join key for row-level
            comparison.  When *None* rows are compared positionally.
        tolerance:
            Acceptable relative row-count difference (0–1).  E.g. 0.01
            allows a 1 % discrepancy.

        Returns
        -------
        ValidationReport
        """
        report = ValidationReport(
            workflow_name=workflow_name,
            row_count_input=len(input_rows),
            row_count_output=len(output_rows),
        )

        # --- Schema validation ------------------------------------------
        input_schema = self._infer_schema(input_rows)
        output_schema = self._infer_schema(output_rows)
        report.column_mismatches = self._compare_schemas(input_schema, output_schema)

        # --- Row count validation ----------------------------------------
        if input_rows and output_rows:
            ratio = abs(len(input_rows) - len(output_rows)) / max(len(input_rows), 1)
            if ratio > tolerance:
                report.notes.append(
                    f"Row count differs by {ratio:.1%} (tolerance={tolerance:.1%})"
                )

        # --- Row-level diff (sample, max 10 rows) -----------------------
        if key_columns:
            report.sample_diffs = self._keyed_diff(
                input_rows, output_rows, key_columns
            )[:10]
        else:
            report.sample_diffs = self._positional_diff(input_rows, output_rows)[:10]

        # --- Overall pass/fail ------------------------------------------
        report.passed = (
            report.row_count_match
            and report.schema_match
            and len(report.sample_diffs) == 0
        )
        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_schema(rows: List[Dict[str, Any]]) -> Dict[str, str]:
        """Return ``{column_name: python_type_name}`` for *rows*."""
        schema: Dict[str, str] = {}
        for row in rows:
            for col, val in row.items():
                if col not in schema:
                    schema[col] = type(val).__name__
        return schema

    @staticmethod
    def _compare_schemas(
        input_schema: Dict[str, str],
        output_schema: Dict[str, str],
    ) -> List[ColumnMismatch]:
        mismatches: List[ColumnMismatch] = []
        all_cols = set(input_schema) | set(output_schema)
        for col in sorted(all_cols):
            in_type = input_schema.get(col)
            out_type = output_schema.get(col)
            if in_type is None:
                mismatches.append(
                    ColumnMismatch(col, "missing_in_input", None, out_type)
                )
            elif out_type is None:
                mismatches.append(
                    ColumnMismatch(col, "missing_in_output", in_type, None)
                )
            elif in_type != out_type:
                mismatches.append(
                    ColumnMismatch(col, "type_mismatch", in_type, out_type)
                )
        return mismatches

    @staticmethod
    def _positional_diff(
        input_rows: List[Dict[str, Any]],
        output_rows: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Return rows that differ when compared by position."""
        diffs: List[Dict[str, Any]] = []
        for i, (in_row, out_row) in enumerate(zip(input_rows, output_rows)):
            if in_row != out_row:
                diffs.append({"row_index": i, "input": in_row, "output": out_row})
        return diffs

    @staticmethod
    def _keyed_diff(
        input_rows: List[Dict[str, Any]],
        output_rows: List[Dict[str, Any]],
        key_columns: List[str],
    ) -> List[Dict[str, Any]]:
        """Return rows that differ when joined on *key_columns*."""

        def make_key(row: Dict[str, Any]) -> Tuple:
            return tuple(row.get(k) for k in key_columns)

        output_index = {make_key(r): r for r in output_rows}
        diffs: List[Dict[str, Any]] = []
        for in_row in input_rows:
            key = make_key(in_row)
            out_row = output_index.get(key)
            if out_row is None:
                diffs.append({"key": key, "issue": "missing_in_output", "input": in_row})
            elif in_row != out_row:
                diffs.append({"key": key, "issue": "value_mismatch", "input": in_row, "output": out_row})
        for out_row in output_rows:
            key = make_key(out_row)
            if key not in {make_key(r) for r in input_rows}:
                diffs.append({"key": key, "issue": "missing_in_input", "output": out_row})
        return diffs
