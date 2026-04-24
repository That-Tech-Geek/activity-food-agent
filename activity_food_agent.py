import os
import sys
import time
import yaml
import sqlite3
import logging
import psutil
import ctypes
import requests
import json
from collections import deque
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from bs4 import BeautifulSoup

# Try to import Windows specific libraries
try:
    import uiautomation as auto
    import win32gui
    import win32process
    WINDOWS_LIBS_AVAILABLE = True
except ImportError:
    WINDOWS_LIBS_AVAILABLE = False

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

class ActivitySensors:
    """Provides tools for sensing computer activity."""
    
    @staticmethod
    def get_cpu_metrics() -> Dict[str, Any]:
        """Returns CPU usage and basic system metrics."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "process_count": len(psutil.pids()),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }

    @staticmethod
    def get_window_list(max_count: int = 15) -> List[Dict[str, str]]:
        """Returns a list of open window titles and their processes."""
        windows = []
        if not WINDOWS_LIBS_AVAILABLE:
            return [{"title": "Platform not supported", "process": "unknown"}]

        def enum_windows_proc(hwnd, l_param):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                title = win32gui.GetWindowText(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    proc = psutil.Process(pid).name()
                except:
                    proc = "unknown"
                windows.append({"title": title, "process": proc})
            return True

        win32gui.EnumWindows(enum_windows_proc, None)
        return windows[:max_count]

    @staticmethod
    def crawl_active_webpage(timeout: float = 5.0) -> Dict[str, Any]:
        """Attempts to find the URL of the active browser and crawl its content."""
        if not WINDOWS_LIBS_AVAILABLE:
            return {"error": "UI Automation not available"}

        try:
            # Find the active window
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc_name = psutil.Process(pid).name().lower()
            
            browser_names = ["chrome.exe", "msedge.exe", "brave.exe", "firefox.exe", "opera.exe"]
            if proc_name not in browser_names:
                return {"status": "Active window is not a supported browser", "process": proc_name}

            # Use UI Automation to find the address bar
            # This is a bit slow and can be brittle depending on browser version
            root = auto.GetRootControl()
            window = auto.WindowControl(searchDepth=1, Name=win32gui.GetWindowText(hwnd))
            
            # Look for the address bar (EditControl or similar)
            address_control = window.EditControl(searchDepth=5, Name="Address and search bar")
            if not address_control.Exists(1): # Try generic names with 1s timeout
                address_control = window.EditControl(searchDepth=5)
            
            if not address_control.Exists(1):
                return {"status": "Could not find address bar", "process": proc_name}

            url = address_control.GetValuePattern().Value
            
            if not url or not url.startswith("http"):
                return {"status": "Could not extract URL", "process": proc_name}

            # Crawl the webpage
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "FoodAgent/1.0"})
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                title = soup.title.string if soup.title else ""
                meta_desc = ""
                meta = soup.find("meta", attrs={"name": "description"})
                if meta:
                    meta_desc = meta.get("content", "")
                
                return {
                    "url": url,
                    "title": title,
                    "description": meta_desc[:200], # Snippet
                    "text_snippet": soup.get_text()[:500].strip()
                }
            else:
                return {"url": url, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.debug(f"Crawling failed: {e}")
            return {"error": str(e)}

class OllamaAnalyzer:
    """Handles interaction with FunctionGemma via Ollama using tool calling."""
    
    def __init__(self, config: Dict):
        self.config = config.get('ollama', {})
        self.host = self.config.get('host', "http://localhost:11434")
        self.model = self.config.get('model', "functiongemma:latest")
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_system_metrics",
                    "description": "Get CPU usage, memory, and process count",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_window_list",
                    "description": "Get titles and process names of all open windows",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "crawl_active_webpage",
                    "description": "Crawl the content of the currently active browser tab",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    def analyze_activity(self) -> Dict[str, Any]:
        """Calls FunctionGemma to analyze activity. Pre-gathers data for reliability."""
        
        metrics = ActivitySensors.get_cpu_metrics()
        windows = ActivitySensors.get_window_list()
        web_context = ActivitySensors.crawl_active_webpage()
        
        system_prompt = "You are a precise activity analysis bot. You MUST return ONLY a JSON object. No other text."
        user_prompt = f"""
Determine the user's mental state from this data:
- System Metrics: {json.dumps(metrics)}
- Open Windows: {json.dumps(windows)}
- Web Context: {json.dumps(web_context)}

JSON format:
{{
  "activity_index": <0-100>,
  "state": "INTENSE" or "FUN",
  "reasoning": "<reason>"
}}
"""
        
        try:
            response = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0
                    }
                },
                timeout=45
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('message', {}).get('content', '{}')
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Fallback for non-JSON responses
                    logger.warning(f"LLM returned non-JSON: {content[:100]}")
                    return {"activity_index": 50, "state": "FUN", "reasoning": "Failed to parse LLM JSON"}
            
            return {"activity_index": 50, "state": "FUN", "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {"activity_index": 50, "state": "FUN", "error": str(e)}

class ActivityFoodAgent:
    def __init__(self, config_path: str = "config.yaml", db_path: str = "agent_log.db"):
        self.config_path = config_path
        self.db_path = db_path
        self.config = self.load_config()
        self.analyzer = OllamaAnalyzer(self.config)
        self.last_order_time = datetime.min
        self.setup_db()
        
    def load_config(self) -> Dict:
        """Loads configuration from YAML file or creates default."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file {self.config_path} not found. Creating default.")
            default_config = {
                'work_applications': ['code', 'cursor', 'terminal'],
                'fun_applications': ['spotify', 'chrome', 'netflix'],
                'intensity_threshold': 0.6,
                'sampling_window_minutes': 10,
                'check_interval_seconds': 60,
                'auto_order': False,
                'budget_limit': 1500,
                'ollama': {'host': 'http://localhost:11434', 'model': 'functiongemma:latest', 'activity_index_threshold': 70},
                'preferences': {
                    'intense_work': {'weights': {'nutrition': 0.4, 'convenience': 0.3, 'speed': 0.2, 'rating': 0.1}},
                    'fun': {'weights': {'indulgence': 0.5, 'rating': 0.3, 'value_for_money': 0.2}}
                },
                'meals_database': []
            }
            with open(self.config_path, 'w') as f:
                yaml.safe_dump(default_config, f)
            return default_config
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def setup_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    detected_state TEXT,
                    activity_index INTEGER,
                    chosen_meal_id INTEGER,
                    chosen_meal_name TEXT,
                    price REAL,
                    order_placed BOOLEAN,
                    user_feedback TEXT
                )
            ''')
            conn.commit()

    def score_meal(self, meal: Dict, state: str, activity_index: int) -> float:
        pref_key = 'intense_work' if state == "INTENSE" else 'fun'
        prefs = self.config.get('preferences', {}).get(pref_key, {})
        weights = prefs.get('weights', {})
        
        score = 0.0
        if meal['typical_price'] > self.config.get('budget_limit', 1000):
            return -100.0
        
        # Scaling factor based on activity index intensity
        intensity_mult = activity_index / 100.0

        if state == "INTENSE":
            nutrition_score = (meal['protein_g'] / meal['calories']) * 100 
            conv_match = any(k in meal.get('keywords', []) for k in prefs.get('convenience_keywords', []))
            convenience = meal['convenience_score'] + (0.5 if conv_match else 0)
            speed_score = max(0, (60 - meal['delivery_time_estimate']) / 60)
            
            score += nutrition_score * weights.get('nutrition', 0.4) * intensity_mult
            score += convenience * 10 * weights.get('convenience', 0.3)
            score += speed_score * 10 * weights.get('speed', 0.2)
            score += meal['rating'] * weights.get('rating', 0.1)
            
        else: # FUN state
            indulgence = meal['indulgence_score']
            if prefs.get('indulgence_score_boost', False):
                indulgence *= 1.2
            
            value = (meal['rating'] / meal['typical_price']) * 1000
            
            score += indulgence * 10 * weights.get('indulgence', 0.5)
            score += meal['rating'] * weights.get('rating', 0.3)
            score += value * weights.get('value_for_money', 0.2)

        return round(score, 2)

    def log_decision(self, state: str, index: int, meal: Dict, placed: bool, feedback: str = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO activity_log 
                (detected_state, activity_index, chosen_meal_id, chosen_meal_name, price, order_placed, user_feedback)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (state, index, meal['id'], meal['name'], meal['typical_price'], placed, feedback))
            conn.commit()

    def mock_place_order(self, meal: Dict) -> bool:
        print(f"\n[MOCK ORDER] Successfully ordered: {m['name']} for ₹{m['typical_price']}")
        return True

    def run_agent(self):
        logger.info("Agent started with FunctionGemma + Ollama...")
        check_interval = self.config.get('check_interval_seconds', 60)
        
        try:
            while True:
                # 1. Analyze Activity via LLM
                analysis = self.analyzer.analyze_activity()
                index = analysis.get('activity_index', 50)
                state = analysis.get('state', "FUN")
                reason = analysis.get('reasoning', "No reasoning provided.")
                
                logger.info(f"Activity Index: {index} | State: {state} | Reason: {reason}")
                
                # 2. Decision Logic
                if (datetime.now() - self.last_order_time) > timedelta(hours=3):
                    self.trigger_meal_decision(state, index)
                
                time.sleep(check_interval)
        except KeyboardInterrupt:
            logger.info("Agent stopped.")

    def trigger_meal_decision(self, state: str, index: int):
        meals = self.config.get('meals_database', [])
        scored_meals = [(self.score_meal(m, state, index), m) for m in meals]
        scored_meals.sort(key=lambda x: x[0], reverse=True)
        top_2 = scored_meals[:2]
        
        if not top_2: return

        chosen_meal = top_2[0][1]
        print(f"\n--- AI SUGGESTION ({state} | Index: {index}) ---")
        for i, (score, m) in enumerate(top_2):
            print(f"{i+1}. {m['name']} (Price: ₹{m['typical_price']}, Score: {score})")
        
        choice = input("\nPick a number to order, or press Enter to skip: ").strip()
        if choice in ['1', '2']:
            idx = int(choice) - 1
            selected = top_2[idx][1]
            print(f"[ORDERED] {selected['name']}")
            self.log_decision(state, index, selected, True)
            self.last_order_time = datetime.now()
        else:
            self.log_decision(state, index, chosen_meal, False, "User skipped")

def main():
    agent = ActivityFoodAgent()
    agent.run_agent()

if __name__ == "__main__":
    main()
