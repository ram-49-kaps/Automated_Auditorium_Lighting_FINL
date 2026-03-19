"""
Phase 6: Error Definitions

Deterministic failure handling.
Phase 6 does NOT retry, does NOT swallow errors.
"""

from typing import Optional


class Phase6Error(Exception):
    """Base exception for Phase 6 errors"""
    
    def __init__(self, message: str, phase_name: Optional[str] = None):
        self.phase_name = phase_name
        super().__init__(message)


class HardFailureError(Phase6Error):
    """
    Hard failure - pipeline must stop.
    
    Triggered by:
    - Phase 1 failure
    - Phase 3 failure
    - Phase 4 failure (after fallback exhausted)
    """
    pass


class NonFatalError(Phase6Error):
    """
    Non-fatal error - pipeline continues.
    
    Triggered by:
    - Phase 5 failure
    - Phase 7 failure
    """
    pass


class ConfigurationError(Phase6Error):
    """Invalid pipeline configuration"""
    pass


class ContractViolationError(Phase6Error):
    """
    Output does not conform to contract schema.
    
    Phase 6 enforces ONLY:
    - Scene schema before Phase 4
    - LightingInstruction schema after Phase 4
    """
    pass


class PhaseNotImplementedError(Phase6Error):
    """Phase is not yet implemented (e.g., Phase 8)"""
    pass
