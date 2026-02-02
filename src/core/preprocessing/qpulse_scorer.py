"""
QPulse Score Calculator - DEPRECATED, use qcore_scorer instead.

This module is kept for backward compatibility.
All functionality has been moved to qcore_scorer.py (QPulse renamed to QCore).
"""
# Re-export everything from qcore_scorer for backward compatibility
from .qcore_scorer import (
    CMELevel,
    QCoreConfig as QPulseConfig,
    calculate_qcore_score as calculate_qpulse_score,
    calculate_batch_qcore_scores as calculate_batch_qpulse_scores,
    get_score_distribution,
    _normalize_bool,
)

# Alias for backward compatibility
QBoostConfig = QPulseConfig
calculate_qboost_score = calculate_qpulse_score
calculate_batch_qboost_scores = calculate_batch_qpulse_scores

__all__ = [
    'CMELevel',
    'QPulseConfig',
    'QBoostConfig',
    'calculate_qpulse_score',
    'calculate_qboost_score',
    'calculate_batch_qpulse_scores',
    'calculate_batch_qboost_scores',
    'get_score_distribution',
    '_normalize_bool',
]
