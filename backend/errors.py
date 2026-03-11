"""
Phase 6 — Error Definitions
Custom exceptions for pipeline error handling.
"""


class HardFailureError(Exception):
    """Fatal error that halts the entire pipeline.
    
    Raised by required phases (1, 3, 4) when they cannot produce valid output.
    """
    def __init__(self, phase: str, message: str):
        self.phase = phase
        self.message = message
        super().__init__(f"[{phase}] HARD FAIL: {message}")


class SoftFailureError(Exception):
    """Non-fatal error that allows pipeline to continue with defaults.
    
    Raised by optional phases (2, 5, 7) when they encounter issues.
    The pipeline logs the error and continues with fallback behavior.
    """
    def __init__(self, phase: str, message: str):
        self.phase = phase
        self.message = message
        super().__init__(f"[{phase}] SOFT FAIL: {message}")
