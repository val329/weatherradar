import streamlit as st  # Importing the Streamlit library
import pandas as pd  # data processing, CSV file I/O (e.g. pd.read_csv)
import sqlite3


# data import
with sqlite3.connect("db/weather.db") as conn:
    conn.execute("PRAGMA foreign_keys = 1")
    cursor = conn.cursor()

    query_all = """
    SELECT city_name as City, fulldate as Date, temp as Temperature,  temp_scale as Scale, description as Description
    FROM fact_weather_observation f
    JOIN dim_city c ON f.city_id = c.city_id 
    JOIN dim_date d ON f.date_id = d.date_id
    """

    query_city = """
    SELECT *
    FROM fact_weather_observation f
    JOIN dim_city c ON f.city_id = c.city_id 
    JOIN dim_date d ON f.date_id = d.date_id
    WHERE city_name = 'Athens'
    """

    # df for weather measurements
    df_all = pd.read_sql_query(query_all, conn)             

    # converting Date to date type for further filtering
    df_all["Date"] = pd.to_datetime(df_all["Date"]).dt.date 
    start_date = df_all["Date"].min()

    # df of cities and average temperatures for scatter plot 
    df_temp = df_all.groupby("City")["Temperature"].mean()


## ---------------------------------------------------------------##
# Streamlit app


def apply_filters():
    city = st.session_state["city_select"]
    date = st.session_state["date_picker"]

    filtered = df_all.copy()

    # Apply city filter
    if city:
        filtered = filtered[filtered["City"] == city]

    # Apply date filter
    if date:
        filtered = filtered[filtered["Date"] == date]

    st.session_state["filtered"] = filtered


# initialize filtered df
if "filtered" not in st.session_state:
    st.session_state["filtered"] = df_all

# PAGE START
st.set_page_config(layout="wide")
st.header("Historical weather around the world")            # header
st.sidebar.title("Pages")                                   # sidebar


# FILTERS START

# Reset button
if st.button("Reset all"):
    st.session_state["filtered"] = df_all
    st.session_state["city_select"] = df_all["City"].unique()[0]
    st.rerun()

# filters 
col1, col2 = st.columns(2)

with col1:  # Everything under this goes into the left column
    # Filter Date
    st.date_input("Choose date", value=start_date, key="date_picker", on_change=apply_filters)

with col2:  # Everything under this goes into the right column
    # Filter City
    st.selectbox("Choose city", df_all["City"].unique(), key="city_select", on_change=apply_filters)
# FILTERS END

st.dataframe(st.session_state["filtered"], hide_index=True) # table



st.header("Average temperature by city")            # header

# st.scatter_chart(df_all, x='Date', y='City', color='Temperature')
st.scatter_chart(df_temp, y='Temperature', color='Temperature')




# PAGE END
