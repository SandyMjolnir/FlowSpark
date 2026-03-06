"""
FlowSpark – Intelligent Alteryx to PySpark Migration Accelerator.

Components:
- parser:    Parse Alteryx workflow XML files into an internal AST.
- mapper:    Map every Alteryx tool to its PySpark equivalent.
- generator: Produce Databricks-compatible PySpark notebooks / scripts.
- validator: Compare input and output datasets to verify correctness.
- estimator: Calculate migration effort and surface an estimation report.
"""

from flowspark.parser.alteryx_parser import AlteryxParser
from flowspark.mapper.tool_mapper import ToolMapper
from flowspark.generator.notebook_generator import NotebookGenerator
from flowspark.validator.validation_framework import ValidationFramework
from flowspark.estimator.effort_estimator import EffortEstimator

__all__ = [
    "AlteryxParser",
    "ToolMapper",
    "NotebookGenerator",
    "ValidationFramework",
    "EffortEstimator",
]
