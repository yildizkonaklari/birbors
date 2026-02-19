import json
import os
import datetime
import time

DATA_FILE = "autopilot_data.json"

class AutoPilot:
    def __init__(self):
        self.data = {
            "cash": 100000.0,
            "holdings": {},  # {symbol: {quantity, avg_cost, current_price}}
            "logs": [],      # [{timestamp, action, symbol, price, amount, balance}]
            "active": False,
            "total_value": 100000.0
        }
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge/Update keys safely
                    for k, v in loaded.items():
                        self.data[k] = v
            except Exception as e:
                print(f"AutoPilot Load Error: {e}")
        else:
            self.save_data()

    def save_data(self):
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"AutoPilot Save Error: {e}")

    def log_transaction(self, action, symbol, price, amount, note=""):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "action": action,
            "symbol": symbol,
            "price": price,
            "amount": amount,
            "total": price * amount,
            "balance": self.data["cash"],
            "note": note
        }
        self.data["logs"].insert(0, log_entry) # Add to top
        # Keep last 100 logs
        if len(self.data["logs"]) > 100:
            self.data["logs"] = self.data["logs"][:100]
        self.save_data()

    def toggle(self, state):
        self.data["active"] = bool(state)
        self.save_data()
        return self.data["active"]

    def calculate_portfolio_value(self):
        stock_value = 0.0
        for sym, item in self.data["holdings"].items():
            qty = item.get("quantity", 0)
            # Use current_price if available, else avg_cost (fallback)
            price = item.get("current_price", item.get("avg_cost", 0))
            stock_value += qty * price
        
        self.data["total_value"] = self.data["cash"] + stock_value
        return self.data["total_value"]

    def process_signals(self, signals):
        if not self.data["active"]:
            return "AutoPilot is OFF"

        if not signals:
            return "No signals"

        for signal in signals:
            symbol = signal["symbol"]
            price = float(signal["price"])
            status = signal["status"] # 'AL' or 'SAT'
            
            # --- BUY LOGIC ---
            if status == 'AL':
                if symbol not in self.data["holdings"]:
                    # Allocation Strategy: Max 10% of Total Value per Trade
                    # Re-calculate total value first
                    total_val = self.calculate_portfolio_value()
                    target_allocation = total_val * 0.10
                    
                    if self.data["cash"] >= target_allocation:
                        # Buy amount
                        amount = int(target_allocation / price)
                        if amount > 0:
                            cost = amount * price
                            self.data["cash"] -= cost
                            self.data["holdings"][symbol] = {
                                "quantity": amount,
                                "avg_cost": price,
                                "current_price": price,
                                "stop_loss": signal.get("stop_loss", price * 0.95)
                            }
                            self.log_transaction("ALIM", symbol, price, amount, f"Sinyal: {signal.get('note', '')}")
                            print(f"[AutoPilot] ALIM: {symbol} x {amount} @ {price}")

            # --- SELL LOGIC ---
            elif status == 'SAT':
                if symbol in self.data["holdings"]:
                    item = self.data["holdings"][symbol]
                    amount = item["quantity"]
                    if amount > 0:
                        revenue = amount * price
                        self.data["cash"] += revenue
                        del self.data["holdings"][symbol]
                        self.log_transaction("SATIŞ", symbol, price, amount, f"Sinyal: {signal.get('note', '')}")
                        print(f"[AutoPilot] SATIŞ: {symbol} x {amount} @ {price}")

        self.save_data()
        return "Signals processed"

    def check_stops(self, current_prices_dict):
        """
        Checks if any holding has hit its stop loss based on current market prices.
        current_prices_dict: { 'GARAN.IS': 102.5, ... }
        """
        if not self.data["active"]: return

        sold_symbols = []
        for symbol, item in list(self.data["holdings"].items()):
            current_price = current_prices_dict.get(symbol)
            
            # Update current price in memory for UI
            if current_price:
                item["current_price"] = current_price

            stop_loss = item.get("stop_loss")
            
            if current_price and stop_loss and current_price <= stop_loss:
                # TRIGGER STOP LOSS
                amount = item["quantity"]
                revenue = amount * current_price
                self.data["cash"] += revenue
                
                self.log_transaction("STOP", symbol, current_price, amount, f"Stop Loss Tetiklendi ({stop_loss})")
                print(f"[AutoPilot] STOP-LOSS: {symbol} @ {current_price}")
                sold_symbols.append(symbol)

        for sym in sold_symbols:
            del self.data["holdings"][sym]
            
        if sold_symbols:
            self.save_data()

    def get_status(self):
        self.calculate_portfolio_value() # Update totals
        return self.data

    def reset(self):
        self.data = {
            "cash": 100000.0,
            "holdings": {},
            "logs": [],
            "active": False,
            "total_value": 100000.0
        }
        self.save_data()
