import sys
import os
import subprocess

def main():
    # Find the path to dashboard.py relative to this script
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.py")
    if not os.path.exists(dashboard_path):
        # Fallback for installed package
        import pkg_resources
        try:
            dashboard_path = pkg_resources.resource_filename('food_ai', 'dashboard.py')
        except:
            print("Error: Could not find dashboard.py")
            return

    subprocess.run(["streamlit", "run", dashboard_path])

if __name__ == "__main__":
    main()
