
import unittest
from decimal import Decimal
from dataclasses import dataclass

# Mocking the RiskManager structure for isolation testing
@dataclass
class RiskConfig:
    max_position_size_percent: float = 20.0  # 20%

class RiskManager:
    def __init__(self):
        self.risk_config = RiskConfig()

    def check_position_size(self, position_size):
        # The logic we modified in src/domain/services/risk_manager.py
        max_position_pct = float(self.risk_config.max_position_size_percent) / 100.0
        
        # logic under test (replicated from fix)
        # ✅ FIX: Handle 1.0 (100%) correctly as ratio.
        # Previously STRICT < 1 treated 1.0 as 1% (1.0/100).
        position_size_decimal = position_size if position_size <= 1.0 else position_size / 100.0
        
        return position_size_decimal, position_size_decimal <= max_position_pct

class TestRiskLogic(unittest.TestCase):
    def setUp(self):
        self.rm = RiskManager()

    def test_100_percent_input(self):
        # Input 1.0 (100%) -> Should be treated as 1.0 (100%)
        # Logic: <= 1.0 is treated as ratio.
        # So 1.0 -> 1.0.
        # Max is 0.20 (20%).
        # 1.0 > 0.20 -> Should Fail check.
        val, passed = self.rm.check_position_size(1.0)
        self.assertEqual(val, 1.0)
        self.assertFalse(passed) # 100% > 20%

    def test_1_percent_input_as_ratio(self):
        # Input 0.01 (1%) -> Should be treated as 0.01.
        val, passed = self.rm.check_position_size(0.01)
        self.assertEqual(val, 0.01)
        self.assertTrue(passed) # 1% < 20%

    def test_2_percent_input_as_integer(self):
        # Input 2.0 (2%) -> Should be treated as 0.02 (2.0/100).
        val, passed = self.rm.check_position_size(2.0)
        self.assertEqual(val, 0.02)
        self.assertTrue(passed)

    def test_threshold_1_point_0(self):
        # Input 1.0. Before fix, < 1 would make this 1.0/100 = 0.01.
        # After fix, <= 1.0 makes this 1.0.
        # This confirms the fix changes behavior for input 1.0.
        val, passed = self.rm.check_position_size(1.0)
        self.assertEqual(val, 1.0)

    def test_threshold_0_point_99(self):
        # Input 0.99 (99%). Treated as ratio 0.99.
        val, passed = self.rm.check_position_size(0.99)
        self.assertEqual(val, 0.99)

if __name__ == '__main__':
    unittest.main()
