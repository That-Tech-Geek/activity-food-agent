import streamlit as st
import yaml
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from activity_food_agent import ActivityFoodAgent, ActivitySensors, OllamaAnalyzer
import os

# Page Config
st.set_page_config(page_title="Food AI Agent Dashboard", layout="wide", page_icon="🍲")

# Styles
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stButton>button { border-radius: 5px; width: 100%; }
    </style>
    """, unsafe_allow_name=True)

# Helper Functions
def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def save_config(config):
    with open("config.yaml", "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)

def get_logs():
    if not os.path.exists("agent_log.db"):
        return pd.DataFrame(columns=["timestamp", "detected_state", "activity_index", "chosen_meal_name", "price", "order_placed"])
    try:
        with sqlite3.connect("agent_log.db") as conn:
            return pd.read_sql_query("SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 50", conn)
    except Exception:
        return pd.DataFrame()

# Initialize Agent components
config = load_config()
analyzer = OllamaAnalyzer(config)

# --- SIDEBAR ---
st.sidebar.title("🍲 Food AI Control")
st.sidebar.info("The agent monitors your activity and decides what to eat based on your work state.")

mode = st.sidebar.radio("Navigation", ["Setup Wizard", "Activity Monitor", "Food Preferences", "User Archetypes", "History"])

# --- MAIN PAGE ---
if mode == "Setup Wizard":
    st.title("🧙‍♂️ Food AI Installation Wizard")
    st.write("Welcome! Let's set up your personal food archetype.")

    # 1. Environment Check
    st.subheader("1. Environment Robustness Check")
    col1, col2, col3 = st.columns(3)
    
    ollama_ok = False
    try:
        requests.get(config.get('ollama', {}).get('host', "http://localhost:11434"), timeout=2)
        col1.success("Ollama: Running")
        ollama_ok = True
    except:
        col1.error("Ollama: Not Found")
        st.warning("Please ensure Ollama is installed and running.")

    if os.path.exists("agent_log.db"):
        col2.success("Database: Ready")
    else:
        col2.info("Database: Will create on run")
        
    if WINDOWS_LIBS_AVAILABLE:
        col3.success("OS Sensors: Active")
    else:
        col3.warning("OS Sensors: Restricted")

    st.divider()

    # 2. Likert Quiz
    st.subheader("2. Food Archetype Quiz")
    st.write("Rate the following statements from 1 (Strongly Disagree) to 5 (Strongly Agree):")

    q1 = st.select_slider("I prioritize high-protein and healthy bowls when I'm in deep work.", options=[1, 2, 3, 4, 5], value=3)
    q2 = st.select_slider("I need food that is easy to eat with one hand while typing.", options=[1, 2, 3, 4, 5], value=3)
    q3 = st.select_slider("I am willing to wait longer for high-quality food during my downtime.", options=[1, 2, 3, 4, 5], value=3)
    q4 = st.select_slider("When I'm relaxing, I want the most indulgent, 'guilty pleasure' foods.", options=[1, 2, 3, 4, 5], value=3)
    q5 = st.select_slider("I prioritize a restaurant's rating over the price of the meal.", options=[1, 2, 3, 4, 5], value=3)

    if st.button("Complete Setup & Save Archetype"):
        # Map Likert to Weights
        # Intense Weights
        config['preferences']['intense_work']['weights']['nutrition'] = q1 / 5.0
        config['preferences']['intense_work']['weights']['convenience'] = q2 / 5.0
        config['preferences']['intense_work']['weights']['speed'] = (6 - q3) / 5.0 # Inverse of wait patience
        
        # Fun Weights
        config['preferences']['fun']['weights']['indulgence'] = q4 / 5.0
        config['preferences']['fun']['weights']['rating'] = q5 / 5.0
        config['preferences']['fun']['weights']['value_for_money'] = (6 - q5) / 5.0 # Inverse of rating priority
        
        save_config(config)
        st.balloons()
        st.success("Setup complete! Your food archetype has been calibrated.")
        st.info("You can now head over to the 'Activity Monitor' to start the agent.")

elif mode == "Activity Monitor":
    st.title("🖥️ Live Activity Monitor")
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        if st.button("Refresh Analysis"):
            with st.spinner("Analyzing with FunctionGemma..."):
                analysis = analyzer.analyze_activity()
                st.session_state.last_analysis = analysis
        
        if 'last_analysis' in st.session_state:
            res = st.session_state.last_analysis
            st.metric("Detected State", res.get('state', 'Unknown'))
            st.write(f"**Reasoning:** {res.get('reasoning', 'N/A')}")
        else:
            st.write("Click refresh to start analysis.")

    with col1:
        index = st.session_state.last_analysis.get('activity_index', 0) if 'last_analysis' in st.session_state else 0
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = index,
            title = {'text': "Activity Index (Work Intensity)"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "#ff4b4b"},
                'steps': [
                    {'range': [0, 40], 'color': "#1a1c24"},
                    {'range': [40, 70], 'color': "#262730"},
                    {'range': [70, 100], 'color': "#3d3f4b"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': config.get('ollama', {}).get('activity_index_threshold', 70)
                }
            }
        ))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white", 'family': "Arial"})
        st.plotly_chart(fig, use_container_width=True)

elif mode == "Food Preferences":
    st.title("🥗 Meal Database Manager")
    st.write("Edit the meals available for the agent to choose from.")
    
    meals_df = pd.DataFrame(config['meals_database'])
    edited_df = st.data_editor(meals_df, num_rows="dynamic", use_container_width=True)
    
    if st.button("Save Meal Database"):
        config['meals_database'] = edited_df.to_dict('records')
        save_config(config)
        st.success("Meal database updated!")

    st.divider()
    st.subheader("Global Constraints")
    config['budget_limit'] = st.number_input("Budget Limit (INR)", value=config['budget_limit'])
    if st.button("Save Constraints"):
        save_config(config)
        st.success("Constraints saved!")

elif mode == "User Archetypes":
    st.title("👤 User Archetypes & Behavior")
    
    tab1, tab2 = st.tabs(["App Mappings", "State Weights"])
    
    with tab1:
        st.subheader("Work Applications")
        work_apps = st.text_area("List apps (one per line)", value="\n".join(config['work_applications']))
        
        st.subheader("Fun Applications")
        fun_apps = st.text_area("List apps (one per line)", value="\n".join(config['fun_applications']))
        
        if st.button("Save App Mappings"):
            config['work_applications'] = [a.strip() for a in work_apps.split("\n") if a.strip()]
            config['fun_applications'] = [a.strip() for a in fun_apps.split("\n") if a.strip()]
            save_config(config)
            st.success("Mappings updated!")

    with tab2:
        st.subheader("Intensity Scaling")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**INTENSE Mode Weights**")
            config['preferences']['intense_work']['weights']['nutrition'] = st.slider("Nutrition Weight", 0.0, 1.0, config['preferences']['intense_work']['weights']['nutrition'])
            config['preferences']['intense_work']['weights']['convenience'] = st.slider("Convenience Weight", 0.0, 1.0, config['preferences']['intense_work']['weights']['convenience'])
        with col2:
            st.write("**FUN Mode Weights**")
            config['preferences']['fun']['weights']['indulgence'] = st.slider("Indulgence Weight", 0.0, 1.0, config['preferences']['fun']['weights']['indulgence'])
            config['preferences']['fun']['weights']['rating'] = st.slider("Rating Weight", 0.0, 1.0, config['preferences']['fun']['weights']['rating'])
            
        if st.button("Save Behavior Weights"):
            save_config(config)
            st.success("Weights updated!")

elif mode == "History":
    st.title("📜 Decision History")
    logs = get_logs()
    if not logs.empty:
        st.dataframe(logs, use_container_width=True)
    else:
        st.write("No history found yet.")
