import sys
import subprocess
import time
import os
import importlib.util

def is_installed(package_name):
    return importlib.util.find_spec(package_name) is not None

def main():
    print("🚀 Verifying Food AI Installation...")
    
    # Check for core package
    if not is_installed("activity_food_agent"):
        print("❌ Error: 'food-ai' package not found in current environment.")
        print("Try running: pip install food-ai")
        return

    # Check for streamlit
    if not is_installed("streamlit"):
        print("📦 Installing missing dependencies (streamlit)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "streamlit"])

    print("✅ Installation Verified.")
    print("🌐 Launching Dashboard...")
    
    # Try to find dashboard.py
    try:
        import activity_food_agent
        dashboard_path = os.path.join(os.path.dirname(activity_food_agent.__file__), "dashboard.py")
    except:
        dashboard_path = "dashboard.py" # Fallback to local
    
    # Launch streamlit
    subprocess.run(["streamlit", "run", dashboard_path])

if __name__ == "__main__":
    main()
