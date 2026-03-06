"""Tests for the CLI."""
import json
import os
import sys
import tempfile

import pytest

from flowspark.cli import main

from tests.fixtures import SIMPLE_WORKFLOW_XML, MACRO_WORKFLOW_XML


def _write_workflow(xml: str, suffix: str = ".yxmd") -> str:
    """Write XML to a temp file and return the path."""
    with tempfile.NamedTemporaryFile(
        suffix=suffix, mode="w", encoding="utf-8", delete=False
    ) as fh:
        fh.write(xml)
        return fh.name


class TestCLIConvert:
    def test_convert_creates_files(self):
        path = _write_workflow(SIMPLE_WORKFLOW_XML)
        tmpdir = tempfile.mkdtemp()
        try:
            rc = main(["convert", path, "-o", tmpdir])
            assert rc == 0
            files = os.listdir(tmpdir)
            exts = {os.path.splitext(f)[1] for f in files}
            assert ".py" in exts
            assert ".ipynb" in exts
            assert ".md" in exts
        finally:
            os.unlink(path)

    def test_convert_py_only(self):
        path = _write_workflow(SIMPLE_WORKFLOW_XML)
        tmpdir = tempfile.mkdtemp()
        try:
            rc = main(["convert", path, "-o", tmpdir, "--formats", "py"])
            assert rc == 0
            files = os.listdir(tmpdir)
            exts = {os.path.splitext(f)[1] for f in files}
            assert ".py" in exts
            assert ".ipynb" not in exts
        finally:
            os.unlink(path)

    def test_convert_with_estimate_flag(self, capsys):
        path = _write_workflow(SIMPLE_WORKFLOW_XML)
        tmpdir = tempfile.mkdtemp()
        try:
            rc = main(["convert", path, "-o", tmpdir, "--estimate"])
            assert rc == 0
            captured = capsys.readouterr()
            assert "TOTAL" in captured.out
        finally:
            os.unlink(path)

    def test_convert_with_json_report(self):
        path = _write_workflow(SIMPLE_WORKFLOW_XML)
        tmpdir = tempfile.mkdtemp()
        try:
            rc = main(["convert", path, "-o", tmpdir, "--json-report"])
            assert rc == 0
            json_files = [f for f in os.listdir(tmpdir) if f.endswith(".json")]
            assert len(json_files) == 1
            with open(os.path.join(tmpdir, json_files[0])) as fh:
                data = json.load(fh)
            assert "total_hours" in data
        finally:
            os.unlink(path)

    def test_convert_nonexistent_file(self):
        rc = main(["convert", "/nonexistent/file.yxmd"])
        assert rc == 1


class TestCLIEstimate:
    def test_estimate_prints_dashboard(self, capsys):
        path = _write_workflow(SIMPLE_WORKFLOW_XML)
        try:
            rc = main(["estimate", path])
            assert rc == 0
            captured = capsys.readouterr()
            assert "TOTAL" in captured.out
        finally:
            os.unlink(path)

    def test_estimate_nonexistent_file(self):
        rc = main(["estimate", "/nonexistent/file.yxmd"])
        assert rc == 1


class TestCLIValidate:
    def _write_json(self, data: list) -> str:
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", encoding="utf-8", delete=False
        ) as fh:
            json.dump(data, fh)
            return fh.name

    def test_validate_identical_passes(self):
        rows = [{"id": 1, "name": "Alice"}]
        a = self._write_json(rows)
        b = self._write_json(rows)
        try:
            rc = main(["validate", a, b])
            assert rc == 0
        finally:
            os.unlink(a)
            os.unlink(b)

    def test_validate_different_fails(self):
        a = self._write_json([{"id": 1}])
        b = self._write_json([{"id": 2}])
        try:
            rc = main(["validate", a, b])
            assert rc == 1
        finally:
            os.unlink(a)
            os.unlink(b)

    def test_validate_with_key_columns(self):
        rows = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
        a = self._write_json(rows)
        b = self._write_json(list(rows))
        try:
            rc = main(["validate", a, b, "--keys", "id"])
            assert rc == 0
        finally:
            os.unlink(a)
            os.unlink(b)
