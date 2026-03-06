"""Tests for the notebook generator."""
import json
import os
import tempfile

import pytest

from flowspark.parser import AlteryxParser
from flowspark.mapper import ToolMapper
from flowspark.generator import NotebookGenerator

from .fixtures import SIMPLE_WORKFLOW_XML, JOIN_WORKFLOW_XML, MACRO_WORKFLOW_XML


def _workflow(xml, name="test"):
    return AlteryxParser().parse_string(xml, name)


class TestNotebookGeneratorPy:
    def setup_method(self):
        self.wf = _workflow(SIMPLE_WORKFLOW_XML, "simple_wf")
        self.mapped = ToolMapper().map_workflow(self.wf)
        self.tmpdir = tempfile.mkdtemp()
        self.gen = NotebookGenerator()

    def test_py_file_created(self):
        written = self.gen.generate(self.wf, self.mapped, self.tmpdir, formats=["py"])
        assert "py" in written
        assert os.path.exists(written["py"])

    def test_py_file_contains_spark_session(self):
        written = self.gen.generate(self.wf, self.mapped, self.tmpdir, formats=["py"])
        with open(written["py"], encoding="utf-8") as fh:
            content = fh.read()
        assert "SparkSession" in content

    def test_py_file_contains_all_tool_snippets(self):
        written = self.gen.generate(self.wf, self.mapped, self.tmpdir, formats=["py"])
        with open(written["py"], encoding="utf-8") as fh:
            content = fh.read()
        for tool_id in self.wf.tools:
            assert f"Tool {tool_id}" in content

    def test_py_databricks_header(self):
        written = self.gen.generate(self.wf, self.mapped, self.tmpdir, formats=["py"])
        with open(written["py"], encoding="utf-8") as fh:
            first_line = fh.readline()
        assert "Databricks notebook source" in first_line


class TestNotebookGeneratorIpynb:
    def setup_method(self):
        self.wf = _workflow(SIMPLE_WORKFLOW_XML, "simple_wf")
        self.mapped = ToolMapper().map_workflow(self.wf)
        self.tmpdir = tempfile.mkdtemp()
        self.gen = NotebookGenerator()

    def test_ipynb_file_created(self):
        written = self.gen.generate(self.wf, self.mapped, self.tmpdir, formats=["ipynb"])
        assert "ipynb" in written
        assert os.path.exists(written["ipynb"])

    def test_ipynb_valid_json(self):
        written = self.gen.generate(self.wf, self.mapped, self.tmpdir, formats=["ipynb"])
        with open(written["ipynb"], encoding="utf-8") as fh:
            nb = json.load(fh)
        assert "cells" in nb
        assert nb["nbformat"] == 4

    def test_ipynb_has_code_cells(self):
        written = self.gen.generate(self.wf, self.mapped, self.tmpdir, formats=["ipynb"])
        with open(written["ipynb"], encoding="utf-8") as fh:
            nb = json.load(fh)
        code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
        assert len(code_cells) >= 2  # at least setup cell + one tool cell


class TestNotebookGeneratorMarkdown:
    def setup_method(self):
        self.wf = _workflow(SIMPLE_WORKFLOW_XML, "simple_wf")
        self.mapped = ToolMapper().map_workflow(self.wf)
        self.tmpdir = tempfile.mkdtemp()
        self.gen = NotebookGenerator()

    def test_md_file_created(self):
        written = self.gen.generate(self.wf, self.mapped, self.tmpdir, formats=["md"])
        assert "md" in written
        assert os.path.exists(written["md"])

    def test_md_contains_tool_table(self):
        written = self.gen.generate(self.wf, self.mapped, self.tmpdir, formats=["md"])
        with open(written["md"], encoding="utf-8") as fh:
            content = fh.read()
        assert "Tool Inventory" in content
        assert "| Tool ID |" in content

    def test_md_contains_workflow_name(self):
        written = self.gen.generate(self.wf, self.mapped, self.tmpdir, formats=["md"])
        with open(written["md"], encoding="utf-8") as fh:
            content = fh.read()
        assert "simple_wf" in content

    def test_md_flags_unsupported(self):
        wf = _workflow(MACRO_WORKFLOW_XML, "macro_wf")
        mapped = ToolMapper().map_workflow(wf)
        written = self.gen.generate(wf, mapped, self.tmpdir, formats=["md"])
        with open(written["md"], encoding="utf-8") as fh:
            content = fh.read()
        assert "Manual" in content or "Unsupported" in content


class TestNotebookGeneratorDocumentation:
    def test_generate_documentation_returns_string(self):
        wf = _workflow(SIMPLE_WORKFLOW_XML, "doc_wf")
        mapped = ToolMapper().map_workflow(wf)
        doc = NotebookGenerator().generate_documentation(wf, mapped)
        assert isinstance(doc, str)
        assert "doc_wf" in doc

    def test_documentation_auto_maps_if_no_mapped(self):
        wf = _workflow(SIMPLE_WORKFLOW_XML, "doc_wf2")
        doc = NotebookGenerator().generate_documentation(wf)
        assert "Tool Inventory" in doc


class TestNotebookGeneratorAllFormats:
    def test_all_formats_written(self):
        wf = _workflow(SIMPLE_WORKFLOW_XML, "all_fmt")
        mapped = ToolMapper().map_workflow(wf)
        tmpdir = tempfile.mkdtemp()
        written = NotebookGenerator().generate(wf, mapped, tmpdir)
        assert set(written.keys()) == {"py", "ipynb", "md"}
