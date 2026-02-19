import unittest
import os
import json
from autopilot import AutoPilot

# Mock Data File for Testing
TEST_DATA_FILE = "autopilot_test_data.json"

class TestAutoPilot(unittest.TestCase):
    def setUp(self):
        # Redirect data file to test file
        global DATA_FILE
        # Patching the filename in the class instance is tricky without modifying the class, 
        # so we will rely on cleanups or just temporary file usage if possible.
        # Ideally AutoPilot should accept a filename arg.
        # For now, let's just use the class as is but handle the cleanup of the default file if it gets created? 
        # No, that's dangerous.
        # Let's Modify AutoPilot temporarily or just import it and monkeypatch the global variable if possible.
        
        import autopilot
        autopilot.DATA_FILE = TEST_DATA_FILE
        
        if os.path.exists(TEST_DATA_FILE):
            os.remove(TEST_DATA_FILE)
            
        self.ap = AutoPilot()
        self.ap.reset() # Start fresh

    def tearDown(self):
        if os.path.exists(TEST_DATA_FILE):
            os.remove(TEST_DATA_FILE)

    def test_initial_state(self):
        status = self.ap.get_status()
        self.assertEqual(status["cash"], 100000.0)
        self.assertEqual(status["active"], False)

    def test_toggle(self):
        self.ap.toggle(True)
        self.assertTrue(self.ap.data["active"])
        self.ap.toggle(False)
        self.assertFalse(self.ap.data["active"])

    def test_buy_logic(self):
        self.ap.toggle(True)
        
        # Signal: BUY GARAN @ 100 TL
        signals = [{
            "symbol": "GARAN.IS",
            "price": 100.0,
            "status": "AL",
            "note": "Test Buy"
        }]
        
        # 10% of 100k = 10k. Price 100. Amount = 100.
        self.ap.process_signals(signals)
        
        status = self.ap.get_status()
        self.assertIn("GARAN.IS", status["holdings"])
        holding = status["holdings"]["GARAN.IS"]
        self.assertEqual(holding["quantity"], 100)
        self.assertEqual(status["cash"], 90000.0) # 100k - 10k

    def test_sell_logic(self):
        # First Buy
        self.ap.toggle(True)
        self.ap.process_signals([{
            "symbol": "GARAN.IS",
            "price": 100.0,
            "status": "AL"
        }])
        
        # Now Sell @ 110
        self.ap.process_signals([{
            "symbol": "GARAN.IS",
            "price": 110.0,
            "status": "SAT"
        }])
        
        status = self.ap.get_status()
        self.assertNotIn("GARAN.IS", status["holdings"])
        # Cash = 90k + (100 * 110) = 90k + 11k = 101k
        self.assertEqual(status["cash"], 101000.0)

    def test_stop_loss(self):
        self.ap.toggle(True)
        # Buy @ 100, Stop defaults to 95
        self.ap.process_signals([{
            "symbol": "GARAN.IS",
            "price": 100.0,
            "status": "AL"
        }])
        
        # Price drops to 94
        current_prices = {"GARAN.IS": 94.0}
        self.ap.check_stops(current_prices)
        
        status = self.ap.get_status()
        self.assertNotIn("GARAN.IS", status["holdings"])
        # Sold @ 94. Cash = 90k + 9.4k = 99.4k
        self.assertEqual(status["cash"], 99400.0)

if __name__ == '__main__':
    unittest.main()
