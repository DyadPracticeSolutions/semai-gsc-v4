"""Deep Audit prompt template.

Exports ``DEEP_AUDIT_PROMPT`` — the full system prompt for generating the
9-section AEO/GEO Executive Audit Addendum from GSC data.
"""

# Re-import the original prompt string to avoid duplicating 700+ lines.
# The original file is kept as the single source of truth.
from deep_audit_prompt import da_prompt as DEEP_AUDIT_PROMPT

__all__ = ["DEEP_AUDIT_PROMPT"]
