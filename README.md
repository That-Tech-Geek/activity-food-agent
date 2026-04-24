# Food Agent Activity Monitoring

An AI agent that monitors computer activity and autonomously (or via confirmation) decides what food to order from Swiggy based on your work state.

## Features
- **Cross-platform Activity Sensing**: Detects focused windows (Windows, macOS, Linux).
- **State Classification**: Uses a rolling window to determine if you are in an `INTENSE` work state or a `FUN` relaxed state.
- **Dynamic Scoring**: Different weights for nutrition, convenience, indulgence, and value based on state.
- **SQLite Logging**: Keeps track of all detected states and ordering decisions.
- **Swiggy Placeholder**: Ready for MCP integration.

## Setup
1. Install the agent:
   ```bash
   pip install food-ai
   ```
2. Configure `config.yaml` with your preferred apps and meals.
3. Run the agent:
   ```bash
   python activity_food_agent.py
   ```

## Development
- `activity_food_agent.py`: Main logic.
- `config.yaml`: Configuration and meal database.
- `agent_log.db`: SQLite database for logs.
