import sys
import os
sys.path.append(os.getcwd())
from activity_food_agent import ActivityFoodAgent
import logging

def test_components():
    print("Starting Component Test...")
    agent = ActivityFoodAgent(config_path="config.yaml")
    
    # Test 1: Window Detection (Mock or Real)
    proc, title = agent.get_active_window_info()
    print(f"Detected Process: {proc}, Title: {title}")
    
    # Test 2: Scoring Engine
    meals = agent.config.get('meals_database', [])
    if meals:
        print("\nTesting Scoring Engine:")
        for state in ["INTENSE", "FUN"]:
            score = agent.score_meal(meals[0], state)
            print(f"Meal: {meals[0]['name']} | State: {state} | Score: {score}")
            
    # Test 3: DB Logging
    print("\nTesting Database Logging...")
    agent.log_decision("INTENSE", meals[0], True, "Test feedback")
    print("Log entry created in agent_log.db")

    # Test 4: State Classification logic check
    from datetime import datetime
    agent.activity_log.clear()
    agent.activity_log.append((datetime.now(), "code.exe", "Visual Studio Code"))
    agent.activity_log.append((datetime.now(), "spotify.exe", "Music"))
    state = agent.classify_state()
    print(f"Classification test (1 work, 1 fun, threshold 0.6): {state}")

if __name__ == "__main__":
    test_components()
