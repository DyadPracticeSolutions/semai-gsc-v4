"""Prompt templates sub-package.

Each module exports a single prompt string used by the report generator.
"""

from prompts.deep_audit import DEEP_AUDIT_PROMPT
from prompts.cluster_audit import CLUSTER_AUDIT_PROMPT
from prompts.comparison import COMPARISON_PROMPT
from prompts.ga4_audit import GA4_AUDIT_PROMPT
from prompts.action_report import ACTION_REPORT_PROMPT

__all__ = [
    "DEEP_AUDIT_PROMPT",
    "CLUSTER_AUDIT_PROMPT",
    "COMPARISON_PROMPT",
    "GA4_AUDIT_PROMPT",
    "ACTION_REPORT_PROMPT",
]
