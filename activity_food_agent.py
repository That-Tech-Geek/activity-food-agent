import os
import sys
import time
import yaml
import sqlite3
import logging
import psutil
import ctypes
from collections import deque
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("FoodAgent")

class ActivityFoodAgent:
    def __init__(self, config_path: str = "config.yaml", db_path: str = "agent_log.db"):
        self.config_path = config_path
        self.db_path = db_path
        self.config = self.load_config()
        self.activity_log = deque()
        self.last_order_time = datetime.min
        self.setup_db()
        
    def load_config(self) -> Dict:
        """Loads configuration from YAML file or creates default."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file {self.config_path} not found. Creating default.")
            # Default config logic would go here if needed, but for now we assume it exists or use internal defaults
            # (In a real scenario, I'd populate a full default dict here)
            pass
        
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            sys.exit(1)

    def setup_db(self):
        """Initializes the SQLite database for logging decisions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS activity_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        detected_state TEXT,
                        chosen_meal_id INTEGER,
                        chosen_meal_name TEXT,
                        price REAL,
                        order_placed BOOLEAN,
                        user_feedback TEXT
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database setup failed: {e}")

    def get_active_window_info(self) -> Tuple[str, str]:
        """Detects the currently focused window's process name and title."""
        try:
            if sys.platform == "win32":
                # Windows implementation
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                window_title = buff.value

                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                process = psutil.Process(pid.value)
                process_name = process.name().lower()
                return process_name, window_title
            
            elif sys.platform == "darwin":
                # macOS placeholder (using AppleScript via subprocess)
                return "mac_placeholder", "Activity"
            else:
                # Linux placeholder
                return "linux_placeholder", "Activity"
        except Exception as e:
            logger.debug(f"Failed to get window info: {e}")
            return "unknown", "Unknown"

    def classify_state(self) -> str:
        """Classifies user state as INTENSE or FUN based on activity window."""
        now = datetime.now()
        window_size = timedelta(minutes=self.config.get('sampling_window_minutes', 10))
        
        # Filter log for items within the sampling window
        while self.activity_log and (now - self.activity_log[0][0]) > window_size:
            self.activity_log.popleft()
            
        if not self.activity_log:
            return "FUN" # Default
            
        work_apps = [app.lower() for app in self.config.get('work_applications', [])]
        work_count = sum(1 for ts, proc, title in self.activity_log if any(app in proc for app in work_apps))
        
        fraction = work_count / len(self.activity_log)
        threshold = self.config.get('intensity_threshold', 0.6)
        
        return "INTENSE" if fraction >= threshold else "FUN"

    def score_meal(self, meal: Dict, state: str) -> float:
        """Scores a meal based on current state and user preferences."""
        pref_key = 'intense_work' if state == "INTENSE" else 'fun'
        prefs = self.config.get('preferences', {}).get(pref_key, {})
        weights = prefs.get('weights', {})
        
        score = 0.0
        
        # Basic constraints
        if meal['typical_price'] > self.config.get('budget_limit', 1000):
            return -100.0
        
        if meal['rating'] < prefs.get('min_rating', 3.5):
            score -= 10.0

        if state == "INTENSE":
            # Nutrition (Protein per Calorie/Price)
            nutrition_score = (meal['protein_g'] / meal['calories']) * 100 
            # Convenience (Keyword matching)
            conv_match = any(k in meal.get('keywords', []) for k in prefs.get('convenience_keywords', []))
            convenience = meal['convenience_score'] + (0.5 if conv_match else 0)
            # Speed
            speed_score = max(0, (60 - meal['delivery_time_estimate']) / 60)
            
            score += nutrition_score * weights.get('nutrition', 0.4)
            score += convenience * 10 * weights.get('convenience', 0.3)
            score += speed_score * 10 * weights.get('speed', 0.2)
            score += meal['rating'] * weights.get('rating', 0.1)
            
        else: # FUN state
            # Indulgence
            indulgence = meal['indulgence_score']
            if prefs.get('indulgence_score_boost', False):
                indulgence *= 1.2
            
            # Value for money (Rating / Price ratio)
            value = (meal['rating'] / meal['typical_price']) * 1000
            
            score += indulgence * 10 * weights.get('indulgence', 0.5)
            score += meal['rating'] * weights.get('rating', 0.3)
            score += value * weights.get('value_for_money', 0.2)

        return round(score, 2)

    def log_decision(self, state: str, meal: Dict, placed: bool, feedback: str = None):
        """Logs the decision to SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO activity_log 
                    (detected_state, chosen_meal_id, chosen_meal_name, price, order_placed, user_feedback)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (state, meal['id'], meal['name'], meal['typical_price'], placed, feedback))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to log decision: {e}")

    def place_order_swiggy(self, meal: Dict) -> bool:
        """
        # TODO: Implement via Swiggy MCP client.
        # Steps: 
        # 1. Connect to Swiggy MCP server
        # 2. Call search_restaurants with preferences
        # 3. Get menu and find meal ID
        # 4. Add to cart
        # 5. Apply best coupon
        # 6. Place order
        """
        logger.info(f"MOCK SWIGGY MCP: Attempting to place order for {meal['name']}...")
        # Placeholder returns False as MCP is pending
        return False

    def mock_place_order(self, meal: Dict) -> bool:
        """Simulates a successful order for testing purposes."""
        print(f"\n[MOCK ORDER] Successfully ordered: {meal['name']} for ₹{meal['typical_price']}")
        print(f"[MOCK ORDER] Estimated delivery: {meal['delivery_time_estimate']} minutes.")
        return True

    def run_agent(self):
        """Main agent loop."""
        logger.info("Agent started. Monitoring activity...")
        check_interval = self.config.get('check_interval_seconds', 60)
        
        try:
            while True:
                # 1. Sense Activity
                proc, title = self.get_active_window_info()
                self.activity_log.append((datetime.now(), proc, title))
                
                # 2. Classify State
                state = self.classify_state()
                logger.info(f"Current Activity: {proc} | State: {state}")
                
                # 3. Decision Logic (e.g., check every 3 hours or on state change)
                # For this demo, we'll trigger a decision if it's been more than 3 hours since last order
                # AND state is stable.
                if (datetime.now() - self.last_order_time) > timedelta(hours=3):
                    self.trigger_meal_decision(state)
                
                time.sleep(check_interval)
        except KeyboardInterrupt:
            logger.info("Agent stopped by user.")

    def trigger_meal_decision(self, state: str):
        """Processes and chooses a meal."""
        logger.info(f"Triggering meal decision for state: {state}")
        meals = self.config.get('meals_database', [])
        
        scored_meals = []
        for meal in meals:
            score = self.score_meal(meal, state)
            scored_meals.append((score, meal))
            
        # Sort by score descending
        scored_meals.sort(key=lambda x: x[0], reverse=True)
        top_2 = scored_meals[:2]
        
        if not top_2:
            logger.warning("No suitable meals found within budget/constraints.")
            return

        chosen_meal = top_2[0][1]
        
        if self.config.get('auto_order', False):
            success = self.mock_place_order(chosen_meal)
            self.log_decision(state, chosen_meal, success)
            self.last_order_time = datetime.now()
        else:
            # Interactive Mode
            print(f"\n--- AI SUGGESTION ({state} MODE) ---")
            for i, (score, m) in enumerate(top_2):
                print(f"{i+1}. {m['name']} (Price: ₹{m['typical_price']}, Score: {score})")
            
            choice = input("\nPick a number to order, or press Enter to skip: ").strip()
            
            if choice in ['1', '2']:
                idx = int(choice) - 1
                selected = top_2[idx][1]
                success = self.mock_place_order(selected)
                self.log_decision(state, selected, success)
                self.last_order_time = datetime.now()
            else:
                logger.info("User skipped order.")
                self.log_decision(state, chosen_meal, False, "User skipped")

if __name__ == "__main__":
    agent = ActivityFoodAgent()
    agent.run_agent()
