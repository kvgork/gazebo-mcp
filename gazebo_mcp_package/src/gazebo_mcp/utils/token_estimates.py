"""
Token estimation constants for MCP response formatting.

Used to estimate how many tokens a response will consume so tools can
apply ResultFilter patterns (summary vs. full) to stay within safe limits.
"""


class TokenEstimates:
    """Per-item token cost constants for different data types."""

    TOKENS_PER_MODEL = 100       # pose, twist, type, name
    TOKENS_PER_SENSOR = 200      # name, type, model, topic, data
    TOKENS_PER_TOPIC = 30        # name + message type
    TOKENS_PER_JOINT = 40        # name + position + velocity + effort

    # Threshold above which summary format is recommended
    SUMMARY_THRESHOLD_TOKENS = 5_000
    # Absolute cap before refusing full output
    MAX_SAFE_TOKENS = 50_000
