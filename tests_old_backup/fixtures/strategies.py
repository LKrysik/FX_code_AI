"""
Strategy test fixtures.

Provides sample strategy configurations for testing:
- Simple strategies
- 4-section strategies (s1, z1, o1, emergency)
"""

import pytest


@pytest.fixture
def sample_strategy():
    """Simple strategy configuration"""
    return {
        'strategy_name': 'Test Simple Strategy',
        'description': 'A simple test strategy',
        'indicators': ['rsi', 'sma_20'],
        'conditions': [
            {'indicator': 'rsi', 'operator': '<', 'value': 30}
        ]
    }


@pytest.fixture
def sample_4section_strategy():
    """Complete 4-section strategy configuration"""
    return {
        'strategy_name': 'Test Momentum Strategy',
        'description': 'A test strategy for momentum trading',
        's1_signal': {
            'conditions': [
                {
                    'id': 'price_velocity_signal',
                    'indicatorId': 'price_velocity',
                    'operator': '>',
                    'value': 0.5
                }
            ]
        },
        'z1_entry': {
            'conditions': [
                {
                    'id': 'price_velocity_entry',
                    'indicatorId': 'price_velocity',
                    'operator': '>',
                    'value': 0.5
                }
            ],
            'positionSize': {
                'type': 'percentage',
                'value': 10
            }
        },
        'o1_cancel': {
            'timeoutSeconds': 300,
            'conditions': [
                {
                    'id': 'price_velocity_cancel',
                    'indicatorId': 'price_velocity',
                    'operator': '<',
                    'value': -0.3
                }
            ]
        },
        'emergency_exit': {
            'conditions': [
                {
                    'id': 'price_velocity_emergency',
                    'indicatorId': 'price_velocity',
                    'operator': '<',
                    'value': -1.0
                }
            ],
            'cooldownMinutes': 60,
            'actions': {
                'cancelPending': True,
                'closePosition': True,
                'logEvent': True
            }
        }
    }
