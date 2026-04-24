# Food Agent Activity Monitoring

An AI agent that monitors computer activity and autonomously (or via confirmation) decides what food to order from Swiggy based on your work state.

## Features
- **Cross-platform Activity Sensing**: Detects focused windows (Windows, macOS, Linux).
- **State Classification**: Uses a rolling window to determine if you are in an `INTENSE` work state or a `FUN` relaxed state.
- **Dynamic Scoring**: Different weights for nutrition, convenience, indulgence, and value based on state.
- **SQLite Logging**: Keeps track of all detected states and ordering decisions.
- **Swiggy Placeholder**: Ready for MCP integration.

## Setup
**Fast Install (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/That-Tech-Geek/activity-food-agent/master/install.ps1 | iex
```

**Manual Installation:**
```bash
pip install food-ai
food-ai-launch
```
2. Configure `config.yaml` with your preferred apps and meals.
3. Run the agent (background):
   ```bash
   python activity_food_agent.py
   ```
4. Launch the Dashboard:
   ```bash
   streamlit run dashboard.py
   ```

## Development
- `activity_food_agent.py`: Main logic.
- `config.yaml`: Configuration and meal database.
- `agent_log.db`: SQLite database for logs.

## Maintainer
- **Sambit Mishra** ([sambit1912@gmail.com](mailto:sambit1912@gmail.com))
