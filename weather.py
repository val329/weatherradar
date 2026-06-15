import pandas as pd  # data processing, CSV file I/O (e.g. pd.read_csv)
import sqlite3

## ---------------------------------------------------------------##
# helper functions


# temperature to float type conversion
def format_temp_to_int(series):
    if series.dtype == "object":
        series = series.str.replace("°F", "", regex=False)
        series = pd.to_numeric(series, errors="coerce")
        print(f"{series.name} converted to float type")
    elif series.dtype == "float64":
        print(f"{series.name} is already a float type")
    else:
        print(f"Could not convert {series.name} series to float type")
    return series


# date and time text to datetime type conversion
def format_text_to_datetime(series):
    if series.dtype == "object":
        series = series.str.replace("UTC (GMT/Zulu)-time: ", "", regex=False)
        series = series.str.replace(" at", ",", regex=False)
        series = pd.to_datetime(series, format="mixed", errors="coerce").dt.date
        print(f"{series.name} converted to datetime type")
    elif series.dtype == "datetime":
        print(f"{series.name} is already a datetime type")
    else:
        print(f"Could not convert {series.name} series to datetime type")
    return series


## ---------------------------------------------------------------##

# loading data from CSV file into a dataframe
df = pd.read_csv("scraped_weather.csv", header=0)
df_cleaned = df.copy()


# DATA CLEANING

# type conversion temperature
df_cleaned["Temperature scale"] = "°F"
df_cleaned["Temperature"] = format_temp_to_int(df["Temperature"])

# type conversion datetime, original format 'UTC (GMT/Zulu)-time: Saturday, June 13, 2026 at 21:08:01'
df_cleaned["UTC time"] = format_text_to_datetime(df["UTC time"])
    #quarter, day of week

# text standartization
df_cleaned["Description"] = df_cleaned["Description"].str.strip().str.lower()
# df_cleaned["City"] = df_cleaned["City"].str.strip().str.lower() #???

# sorting
df_cleaned.sort_values(by='City', ascending=True, inplace=True)

# DATA TRANSFORMATION

def db_create_tables(cursor):         
        """ create 4 tables """

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_city (
            city_id INTEGER PRIMARY KEY,
            city_name TEXT NOT NULL UNIQUE,
            country TEXT, 
            latitude INT, 
            longitude INT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_date (
            date_id INTEGER PRIMARY KEY,
            fulldate INT UNIQUE, 
            year INT, 
            month INT, 
            day INT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_weather_type (
            weather_type_id INTEGER PRIMARY KEY,
            weather_desc TEXT UNIQUE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_weather_observation (
            observation_id INTEGER PRIMARY KEY, 
            city_id INT UNIQUE, 
            date_id INT UNIQUE, 
            temp INT, 
            temp_scale TEXT,
            weather_type_id INTEGER, 
            weather_type_desc TEXT,
            FOREIGN KEY (city_id) REFERENCES dim_city(city_id),
            FOREIGN KEY (date_id) REFERENCES dim_date(date_id),
            FOREIGN KEY (weather_type_id) REFERENCES dim_weather_type(weather_type_id)
        )
        """)

        print("Tables created successfully.")
        conn.commit()


def add_city(cursor, name, country="", latitude=0, longitude=0):
    """ add a new city record into dim_city table """
    try:
        cursor.execute("INSERT INTO dim_city (city_name, country, latitude, longitude) VALUES (?,?,?,?)", 
                       (name, country, latitude, longitude))
    except sqlite3.IntegrityError:
        print(f"{name} is already in the database.")


def add_date(cursor, full, year, month, day):
    """ add a new date record into dim_date table """
    try:
        cursor.execute("INSERT INTO dim_date (fulldate, year, month, day) VALUES (?,?,?,?)", 
                       (full, year, month, day))
    except sqlite3.IntegrityError:
        print(f"Date {year}-{month}-{day} is already in the database.")


def add_weather_type(cursor, desc):
    """ add a new weather type record into dim_weather_type table """
    try:
        cursor.execute("INSERT INTO dim_weather_type (weather_desc) VALUES (?)", 
                       (desc,))
    except sqlite3.IntegrityError:
        print(f"Weather type {desc} is already in the database.")


def add_weather_observation(cursor, city, date, temp, temp_scale, wtype=0, wdesc=""):
    """ add a new weather observation record into fact_weather_observation table """
    try:
        cursor.execute("INSERT INTO fact_weather_observation (city_id, date_id, temp, temp_scale, weather_type_id, weather_type_desc)"
                       "VALUES (?,?,?,?,?,?)", 
                       (city, date, temp, temp_scale, wtype, wdesc))
    except sqlite3.IntegrityError:
        print(f"Weather observation for {city} on {date} is already in the database.")


# connect to a new SQLite database
with sqlite3.connect("db/weather.db") as conn:
    conn.execute("PRAGMA foreign_keys = 1")
    cursor = conn.cursor()

    # '''
    db_create_tables(cursor)

    # adding records for dim_city table from City column
    for city in df_cleaned["City"].unique(): 
        add_city(cursor, city)
        
    # adding records for dim_date table from UTC time column
    for time in df_cleaned["UTC time"]: 
        add_date(cursor, time.strftime("%Y-%m-%d"), time.year, time.month, time.day)
    
    # adding records for dim_weather_type table
    for row in df_cleaned['Description'].unique(): 
        for desc in row.split("."): 
            add_weather_type(cursor, desc.strip())
    # '''

    # adding city_id to the cleaned dataframe
    df_city = pd.read_sql_query("SELECT city_id, city_name as City FROM dim_city", conn)
    df_cleaned_merge = df_cleaned.merge(df_city, on="City", how="left")
    
    # adding date_id to the cleaned dataframe
    df_date = pd.read_sql_query("SELECT date_id, fulldate FROM dim_date", conn)
    df_date["fulldate"] = pd.to_datetime(df_date["fulldate"]).dt.date
    df_cleaned_merge = df_cleaned_merge.merge(df_date, left_on="UTC time", right_on="fulldate", how="left")
    
    # transforming the dataframe to load into database table (drop columns, reorder columns, remove duplicated rows)
    df_cleaned_merge.drop(columns=['City', 'Local time'], axis=1, inplace=True)
    df_cleaned_merge = df_cleaned_merge.rename(columns={'Temperature': 'temp', 'Temperature scale': 'temp_scale', 'Description': 'description'})
    df_cleaned_merge = df_cleaned_merge.reindex(columns=['city_id', 'date_id', 'temp', 'temp_scale', 'description'])  #reordering columns                                      
    df_cleaned_merge = df_cleaned_merge.drop_duplicates(subset=['city_id','date_id'])
    
    # adding data to fact_weather_observation from a cleaned dataframe
    df_cleaned_merge.to_sql(name="fact_weather_observation", con=conn, if_exists="replace", index=False)

    # retrieving the results
    cursor.execute("""
       
        """)
    
    query1 = """
    SELECT *
    FROM fact_weather_observation f
    JOIN dim_city c ON f.city_id = c.city_id 
    JOIN dim_date d ON f.date_id = d.date_id
    WHERE city_name = 'Athens'
    """

    cursor.execute(query1)
    print("query: ", cursor.fetchall())




