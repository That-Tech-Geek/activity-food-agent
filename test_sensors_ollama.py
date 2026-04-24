import os
import sys
import yaml
import json
from activity_food_agent import ActivitySensors, OllamaAnalyzer

def test_sensors():
    print("--- Testing Activity Sensors ---")
    
    print("\n1. System Metrics:")
    metrics = ActivitySensors.get_cpu_metrics()
    print(json.dumps(metrics, indent=2))
    
    print("\n2. Window List (Top 5):")
    windows = ActivitySensors.get_window_list(5)
    print(json.dumps(windows, indent=2))
    
    print("\n3. Active Webpage Crawl:")
    web_context = ActivitySensors.crawl_active_webpage()
    print(json.dumps(web_context, indent=2))

def test_ollama_integration():
    print("\n--- Testing Ollama / FunctionGemma Integration ---")
    if not os.path.exists("config.yaml"):
        print("Error: config.yaml missing")
        return

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    analyzer = OllamaAnalyzer(config)
    print(f"Using model: {analyzer.model} at {analyzer.host}")
    
    print("Calling analyze_activity (this may take a moment)...")
    try:
        analysis = analyzer.analyze_activity()
        print("\nFinal Analysis Result:")
        print(json.dumps(analysis, indent=2))
    except Exception as e:
        print(f"Error during Ollama analysis: {e}")

if __name__ == "__main__":
    test_sensors()
    test_ollama_integration()
