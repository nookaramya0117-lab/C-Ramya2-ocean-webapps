import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import re
from dateutil import parser
from datetime import datetime, timedelta

# -------------------
# Database Connection
# -------------------
conn = sqlite3.connect('argo_data.db')
df = pd.DataFrame()  # initialize

# -------------------
# View All Data Button
# -------------------
if st.sidebar.button("View All ARGO Data"):
    df_all = pd.read_sql_query("SELECT * FROM argo_profiles", conn)
    st.subheader("📂 All ARGO Profiles")
    st.dataframe(df_all)

# -------------------
# Session State
# -------------------
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# -------------------
# Page Layout
# -------------------
st.set_page_config(page_title="FloatChat", layout="wide")
st.title("🌊 FloatChat: AI Ocean Data Explorer")
st.sidebar.header("Options")
show_map = st.sidebar.checkbox("Show Map", True)
show_plot = st.sidebar.checkbox("Show Depth-Time Plot", True)

# -------------------
# Helper function: parse date ranges
# -------------------
def parse_date_range(user_input):
    user_input = user_input.lower()
    today = datetime.today()
    start_date = None
    end_date = None

    # Example: "last 6 months"
    last_months = re.search(r'last (\d+) months', user_input)
    if last_months:
        months = int(last_months.group(1))
        start_date = today - pd.DateOffset(months=months)
        end_date = today

    # Example: "in March 2023" or "2023-03"
    month_year = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* (\d{4})', user_input)
    if month_year:
        month_str = month_year.group(1)
        year = int(month_year.group(2))
        month = datetime.strptime(month_str[:3], '%b').month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year+1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month+1, 1) - timedelta(days=1)

    return start_date, end_date

# -------------------
# Chat Input
# -------------------
user_input = st.text_input("Ask a question about ARGO data:")
if st.button("Send") and user_input:
    user_lower = user_input.lower()
    df = pd.DataFrame()  # reset for each query

    # -------------------
    # Parse date range
    # -------------------
    start_date, end_date = parse_date_range(user_input)

    # -------------------
    # Coordinate-based query
    # -------------------
    coord_match = re.search(r'([-+]?\d+\.?\d*)\s*°?\s*[NnSs]?,?\s*([-+]?\d+\.?\d*)\s*°?\s*[EeWw]?', user_input)
    if coord_match:
        lat = float(coord_match.group(1))
        lon = float(coord_match.group(2))
        query = f"""
            SELECT * FROM argo_profiles
            WHERE latitude BETWEEN {lat - 1} AND {lat + 1}
              AND longitude BETWEEN {lon - 1} AND {lon + 1}
        """
        if start_date and end_date:
            query += f" AND date BETWEEN '{start_date.date()}' AND '{end_date.date()}'"
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            avg_salinity = df['salinity'].mean()
            avg_temp = df['temperature'].mean()
            response = f"Near ({lat}°N, {lon}°E)"
            if start_date:
                response += f" from {start_date.date()} to {end_date.date()}"
            response += f": Average salinity = {avg_salinity:.2f}, Average temperature = {avg_temp:.2f} °C"
        else:
            response = f"No ARGO float data found near ({lat}°N, {lon}°E)"

    # -------------------
    # Generic queries
    # -------------------
    elif "salinity" in user_lower and "equator" in user_lower:
        query = "SELECT * FROM argo_profiles WHERE latitude BETWEEN -5 AND 5"
        if start_date and end_date:
            query += f" AND date BETWEEN '{start_date.date()}' AND '{end_date.date()}'"
        df = pd.read_sql_query(query, conn)
        response = f"Found {len(df)} profiles near the equator."
    
    elif "average salinity" in user_lower:
        query = "SELECT AVG(salinity) AS avg_salinity FROM argo_profiles"
        if start_date and end_date:
            query += f" WHERE date BETWEEN '{start_date.date()}' AND '{end_date.date()}'"
        df = pd.read_sql_query(query, conn)
        response = f"Average salinity: {df['avg_salinity'][0]:.2f}"

    elif "average temperature" in user_lower:
        query = "SELECT AVG(temperature) AS avg_temp FROM argo_profiles"
        if start_date and end_date:
            query += f" WHERE date BETWEEN '{start_date.date()}' AND '{end_date.date()}'"
        df = pd.read_sql_query(query, conn)
        response = f"Average temperature: {df['avg_temp'][0]:.2f} °C"

    elif "highest temperature" in user_lower:
        query = "SELECT float_id, MAX(temperature) AS max_temp FROM argo_profiles"
        if start_date and end_date:
            query = f"SELECT float_id, temperature AS max_temp FROM argo_profiles WHERE date BETWEEN '{start_date.date()}' AND '{end_date.date()}' ORDER BY temperature DESC LIMIT 1"
        df = pd.read_sql_query(query, conn)
        response = f"Float {df['float_id'][0]} has the highest temperature: {df['max_temp'][0]:.2f} °C"

    elif "lowest salinity" in user_lower:
        query = "SELECT float_id, MIN(salinity) AS min_salinity FROM argo_profiles"
        if start_date and end_date:
            query = f"SELECT float_id, salinity AS min_salinity FROM argo_profiles WHERE date BETWEEN '{start_date.date()}' AND '{end_date.date()}' ORDER BY salinity ASC LIMIT 1"
        df = pd.read_sql_query(query, conn)
        response = f"Float {df['float_id'][0]} has the lowest salinity: {df['min_salinity'][0]:.2f}"

    elif "compare" in user_lower:
        query = "SELECT * FROM argo_profiles"
        if start_date and end_date:
            query += f" WHERE date BETWEEN '{start_date.date()}' AND '{end_date.date()}'"
        df = pd.read_sql_query(query, conn)
        response = "Comparison data fetched."

    else:
        response = "Sorry, I don't understand. Try asking about salinity, temperature, coordinates, or date ranges."

    # -------------------
    # Store messages
    # -------------------
    st.session_state['messages'].append({"user": user_input, "bot": response})

# -------------------
# Display Chat
# -------------------
for chat in st.session_state['messages']:
    st.markdown(f"**You:** {chat['user']}")
    st.markdown(f"**FloatChat:** {chat['bot']}")

# -------------------
# Data Visualization
# -------------------
if not df.empty:
    if show_map:
        st.subheader("🌐 Map of ARGO Floats")
        fig_map = px.scatter_mapbox(
            df,
            lat="latitude",
            lon="longitude",
            color="temperature",
            size="salinity",
            hover_name="float_id",
            zoom=1,
            mapbox_style="open-street-map"
        )
        st.plotly_chart(fig_map, use_container_width=True)

    if show_plot:
        st.subheader("📊 Depth vs Temperature")
        fig_plot = px.line(df, x="depth", y="temperature", color="float_id", markers=True)
        st.plotly_chart(fig_plot, use_container_width=True)

# -------------------
# Show Raw Data Table
# -------------------
if not df.empty:
    st.subheader("📋 Raw Data")
    st.dataframe(df)
