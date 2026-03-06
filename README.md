# FlowSpark
Intelligent Alteryx to PySpark Migration Accelerator

FlowSpark automates the migration of Alteryx workflows to Databricks-compatible PySpark
notebooks.  It parses Alteryx XML, maps every tool to its PySpark equivalent, generates
runnable code, documents the transformation, flags anything that needs manual review,
validates output data, and produces an effort-estimation dashboard for planning.

---

## Features

| Capability | Description |
|---|---|
| **XML Parser** | Parses `.yxmd` / `.yxwz` / `.yxmc` workflow files; extracts tools, joins, filters, formulas, macros and connections |
| **Tool Mapper** | Maps 18+ Alteryx tool categories to idiomatic PySpark snippets; flags unsupported components |
| **Notebook Generator** | Emits Databricks-compatible `.py` scripts, Jupyter `.ipynb` notebooks, and Markdown documentation |
| **Validation Framework** | Compares input / output datasets row-by-row (positional or key-based) and reports schema / value mismatches |
| **Effort Estimator** | Calculates per-tool migration hours, assigns complexity tiers, and renders a sprint-planning dashboard |
| **CLI** | `flowspark convert`, `flowspark estimate`, `flowspark validate` |

---

## Supported Alteryx Tools

| Category | PySpark Equivalent |
|---|---|
| InputData | `spark.read.format(...).load(...)` |
| TextInput | `spark.createDataFrame(...)` |
| OutputData | `df.write.format(...).save(...)` |
| Filter | `df.filter(...)` |
| Formula | `df.withColumn(col, expr(...))` |
| MultiFieldFormula | `df.withColumn(col, F.expr(...))` loop |
| Join | `df.join(other, cond, how=...)` |
| Select | `df.select(...)` |
| Sort | `df.orderBy(...)` |
| Sample | `df.limit(n)` / `df.sample(fraction)` |
| RecordID | `df.withColumn(..., F.row_number().over(...))` |
| Summarize | `df.groupBy(...).agg(...)` |
| Unique | `df.dropDuplicates()` |
| AppendFields | `df.crossJoin(other)` |
| Union | `df.unionByName(other)` |
| DataCleanse | Configurable cleansing stub |

**Flagged for manual review:** Spatial, FuzzyMatch, FindReplace, MacroInput, MacroOutput.

---

## Quick Start

### Install

```bash
pip install -e .
```

### Convert a workflow

```bash
flowspark convert my_workflow.yxmd -o output/
```

This writes three files to `output/`:

* `my_workflow.py`    – Databricks notebook source
* `my_workflow.ipynb` – Jupyter notebook
* `my_workflow.md`    – Transformation documentation

### Show the effort dashboard

```bash
flowspark estimate my_workflow.yxmd
```

```
============================================================
  FlowSpark Effort Estimation Dashboard
  Workflow: my_workflow
============================================================
  Tool ID      Category             Hours  Bar
------------------------------------------------------------
  1            InputData              0.5h  ██
  2            Filter                 0.5h  ██
  3            Formula                1.0h  ████
  4            OutputData             0.5h  ██
------------------------------------------------------------
  TOTAL                               2.5h
  Complexity: LOW        Sprints: 0.1
============================================================
```

### Validate output data

```bash
flowspark validate expected.json actual.json --keys id --name my_workflow
```

### Generate effort JSON for planning tools

```bash
flowspark convert my_workflow.yxmd -o output/ --json-report
```

---

## Python API

```python
from flowspark import AlteryxParser, ToolMapper, NotebookGenerator, EffortEstimator

# 1. Parse
workflow = AlteryxParser().parse_file("my_workflow.yxmd")

# 2. Map
mapped = ToolMapper().map_workflow(workflow)

# 3. Generate notebooks + docs
NotebookGenerator().generate(workflow, mapped, output_dir="output/")

# 4. Estimate effort
report = EffortEstimator().estimate(workflow, mapped)
print(report.dashboard_text())
```

### Validation

```python
from flowspark import ValidationFramework

fw = ValidationFramework()
report = fw.validate(
    workflow_name="my_workflow",
    input_rows=[{"id": 1, "name": "Alice"}],
    output_rows=[{"id": 1, "name": "Alice"}],
    key_columns=["id"],
)
print(report.summary())
```

---

## Project Structure

```
src/flowspark/
├── __init__.py            # Public API exports
├── cli.py                 # Command-line interface
├── parser/                # Alteryx XML parser
│   └── __init__.py
├── mapper/                # Tool → PySpark mapping engine
│   └── __init__.py
├── generator/             # Notebook & documentation generator
│   └── __init__.py
├── validator/             # Input/output validation framework
│   └── __init__.py
└── estimator/             # Effort estimation & dashboard
    └── __init__.py
tests/
├── fixtures.py            # Shared sample Alteryx XML fixtures
├── test_parser.py
├── test_mapper.py
├── test_generator.py
├── test_validator.py
├── test_estimator.py
└── test_cli.py
```

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

