"""
QBoost Score Calculator - DEPRECATED, use qcore_scorer instead.

This module is kept for backward compatibility.
All functionality has been moved to qcore_scorer.py as part of the Q-Suite rename.
"""
# Re-export everything from qcore_scorer for backward compatibility
from .qcore_scorer import (
    CMELevel,
    QCoreConfig as QBoostConfig,
    QCoreConfig as QPulseConfig,  # Also alias for qpulse backward compat
    calculate_qcore_score as calculate_qboost_score,
    calculate_qcore_score as calculate_qpulse_score,  # Also alias for qpulse backward compat
    calculate_batch_qcore_scores as calculate_batch_qboost_scores,
    calculate_batch_qcore_scores as calculate_batch_qpulse_scores,
    get_score_distribution,
    _normalize_bool,
)

__all__ = [
    'CMELevel',
    'QBoostConfig',
    'QPulseConfig',
    'calculate_qboost_score',
    'calculate_qpulse_score',
    'calculate_batch_qboost_scores',
    'calculate_batch_qpulse_scores',
    'get_score_distribution',
    '_normalize_bool',
]
