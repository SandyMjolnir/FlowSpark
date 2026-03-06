"""Tests for the validation framework."""
import pytest

from flowspark.validator import ValidationFramework, ValidationReport


class TestValidationFrameworkBasic:
    def setup_method(self):
        self.fw = ValidationFramework()

    def test_identical_datasets_pass(self):
        rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        report = self.fw.validate("wf", rows, list(rows))
        assert report.passed is True

    def test_different_row_counts_fail(self):
        input_rows = [{"id": 1}, {"id": 2}, {"id": 3}]
        output_rows = [{"id": 1}]
        report = self.fw.validate("wf", input_rows, output_rows)
        assert report.passed is False
        assert report.row_count_match is False

    def test_missing_column_in_output(self):
        input_rows = [{"id": 1, "name": "Alice"}]
        output_rows = [{"id": 1}]
        report = self.fw.validate("wf", input_rows, output_rows)
        cols = [cm.column for cm in report.column_mismatches]
        assert "name" in cols

    def test_extra_column_in_output(self):
        input_rows = [{"id": 1}]
        output_rows = [{"id": 1, "extra": "x"}]
        report = self.fw.validate("wf", input_rows, output_rows)
        issues = {cm.column: cm.issue for cm in report.column_mismatches}
        assert issues.get("extra") == "missing_in_input"

    def test_type_mismatch_detected(self):
        input_rows = [{"id": 1}]
        output_rows = [{"id": "1"}]
        report = self.fw.validate("wf", input_rows, output_rows)
        issues = {cm.column: cm.issue for cm in report.column_mismatches}
        assert issues.get("id") == "type_mismatch"

    def test_value_mismatch_positional(self):
        input_rows = [{"id": 1, "val": 10}]
        output_rows = [{"id": 1, "val": 99}]
        report = self.fw.validate("wf", input_rows, output_rows)
        assert len(report.sample_diffs) == 1

    def test_schema_match_property(self):
        rows = [{"id": 1}]
        report = self.fw.validate("wf", rows, list(rows))
        assert report.schema_match is True

    def test_empty_datasets_pass(self):
        report = self.fw.validate("wf", [], [])
        assert report.passed is True


class TestValidationFrameworkKeyedComparison:
    def setup_method(self):
        self.fw = ValidationFramework()

    def test_keyed_match(self):
        rows = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
        report = self.fw.validate("wf", rows, list(rows), key_columns=["id"])
        assert report.passed is True

    def test_keyed_missing_in_output(self):
        input_rows = [{"id": 1}, {"id": 2}]
        output_rows = [{"id": 1}]
        report = self.fw.validate("wf", input_rows, output_rows, key_columns=["id"])
        diffs_issues = [d["issue"] for d in report.sample_diffs]
        assert "missing_in_output" in diffs_issues

    def test_keyed_value_mismatch(self):
        input_rows = [{"id": 1, "val": 10}]
        output_rows = [{"id": 1, "val": 99}]
        report = self.fw.validate("wf", input_rows, output_rows, key_columns=["id"])
        diffs_issues = [d["issue"] for d in report.sample_diffs]
        assert "value_mismatch" in diffs_issues


class TestValidationFrameworkTolerance:
    def test_within_tolerance_no_note(self):
        input_rows = [{"id": i} for i in range(100)]
        output_rows = [{"id": i} for i in range(99)]  # 1 % difference
        fw = ValidationFramework()
        report = fw.validate("wf", input_rows, output_rows, tolerance=0.02)
        # Row count note should NOT be added within tolerance
        row_count_notes = [n for n in report.notes if "Row count" in n]
        assert len(row_count_notes) == 0


class TestValidationReport:
    def test_summary_contains_status(self):
        rows = [{"id": 1}]
        fw = ValidationFramework()
        report = fw.validate("test_wf", rows, list(rows))
        summary = report.summary()
        assert "PASSED" in summary

    def test_summary_contains_workflow_name(self):
        fw = ValidationFramework()
        report = fw.validate("my_workflow", [], [])
        assert "my_workflow" in report.summary()
