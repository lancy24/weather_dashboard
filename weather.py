
# ---------- 1. IMPORTS ----------
import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ---------- 2. PAGE SETTINGS ----------
st.set_page_config(page_title="Weather Dashboard", page_icon="🌦️",layout="wide",initial_sidebar_state="expanded")


# ---------- 3. API LINKS ----------
url1= "https://api.open-meteo.com/v1/forecast"
url2="https://geocoding-api.open-meteo.com/v1/search"

# ---------- 4. HELPER FUNCTIONS ----------
@st.cache_data(ttl=600)
def get_location(city):
    r=requests.get(url2, params={"name":city,"count":1},timeout=10)
    r.raise_for_status()
    results= r.json().get("results")
    if not results:
        return None
    return results[0]


@st.cache_data(ttl=600)
def get_weather(lat, lon, unit, days):
    params = {
        "latitude": lat,
        "longitude": lon,
    
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                   "wind_speed_10m,pressure_msl,weather_code",
 
        "hourly": "temperature_2m",
      
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
                 "sunrise,sunset,uv_index_max",
        "temperature_unit": unit,          
        "timezone": "auto",                
        "forecast_days": days,   
        "models": "gfs_seamless",           
    }
    r = requests.get(url1, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def describe(code):
    
    if code == 0:
        return "☀️", "Clear sky"
    if code in (1, 2, 3):
        return "⛅", "Partly cloudy"
    if code in (45, 48):
        return "🌫️", "Fog"
    if code in (51, 53, 55, 56, 57):
        return "🌦️", "Drizzle"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "🌧️", "Rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "❄️", "Snow"
    if code in (95, 96, 99):
        return "⛈️", "Thunderstorm"
    return "🌡️", "Unknown"


def uv_label(uv):
    if uv < 3:
        return "Low"
    if uv < 6:
        return "Moderate"
    if uv < 8:
        return "High"
    return "Very high"

 #--------- 5. TITLE ----------
st.title("🌦️ Weather Dashboard")

# ---------- 6. SIDEBAR ----------
st.sidebar.header("Settings")
city=st.sidebar.text_input("city name",placeholder="enter city name")
unit=st.sidebar.radio("Unit",["Celsius","Fahrenheit"])
days = st.sidebar.slider("Forecast days", min_value=3, max_value=7, value=7)
city = city.strip()  
if not city:
    st.warning("⚠️enter city name")
    st.stop()

symbol = "°C" if unit == "Celsius" else "°F"
api_unit = unit.lower() 

#-------7. ERROR HANDLING-------
try:
    with st.spinner("Loading"):                
        place = get_location(city)                              
        if place is None:
            st.error("City not found")
            st.stop()                                          
        data = get_weather(place["latitude"], place["longitude"], api_unit, days) 
except requests.RequestException:
    st.error("Try later")
    st.stop()

#-------8.DATA VARIABLES-----------
cur = data["current"]       
hourly = data["hourly"]       
daily = data["daily"]        

temp = cur["temperature_2m"]
feels = cur["apparent_temperature"]
humidity = cur["relative_humidity_2m"]
wind = cur["wind_speed_10m"]
pressure = cur["pressure_msl"]
icon, condition = describe(cur["weather_code"])

#----------9.CITY NAME--------------
place_name = ", ".join(filter(None, [place["name"], place.get("admin1"), place.get("country")]))
st.subheader(f"📍 {place_name}")

#----------10.HERO CARD----------
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    c1.metric("Temperature", f"{temp} {symbol}")
    c2.metric("Feels like", f"{feels} {symbol}")
    c3.markdown(f"### {icon} {condition}")

#-------11.HOURLY STRIP---------
st.subheader("Next hours")
now_hour = cur["time"][:13] + ":00"
start = hourly["time"].index(now_hour) if now_hour in hourly["time"] else 0

hour_cols = st.columns(5)
for i, col in enumerate(hour_cols):
    idx = start + i * 3
    if idx >= len(hourly["time"]):
        break
    t = datetime.strptime(hourly["time"][idx], "%Y-%m-%dT%H:%M")
    label = "Now" if i == 0 else t.strftime("%I %p").lstrip("0")
    col.metric(label, f"{hourly['temperature_2m'][idx]} {symbol}")


#-----------12.DETAIL TILES--------------
st.subheader("Details")
d1, d2, d3, d4 = st.columns(4)
d1.metric("Humidity", f"{humidity} %")
d2.metric("Wind", f"{wind} km/h")
uv = daily["uv_index_max"][0]
d3.metric("UV index", f"{uv} ({uv_label(uv)})")
d4.metric("Pressure", f"{round(pressure)} hPa")

#--------DAILY FORECAST TABLE------
st.subheader(f"{days}-day forecast")
df = pd.DataFrame({
    "Date": [datetime.strptime(d, "%Y-%m-%d").strftime("%a %d %b") for d in daily["time"]],
    "Max": daily["temperature_2m_max"],
    "Min": daily["temperature_2m_min"],
    "Rain %": daily["precipitation_probability_max"],
})
df["Rain %"] = df["Rain %"].fillna(0)

st.dataframe(
    df,
    hide_index=True,
    column_config={
        "Max": st.column_config.NumberColumn(f"Max ({symbol})"),
        "Min": st.column_config.NumberColumn(f"Min ({symbol})"),
        "Rain %": st.column_config.ProgressColumn(
            "Rain chance", min_value=0, max_value=100, format="%d%%"
        ),
    },
)

# ---------- 14. TEMPERATURE TREND CHART ----------
st.subheader("Temperature trend")
st.line_chart(df.set_index("Date")[["Max", "Min"]])
# ---------- 15. SUNRISE / SUNSET ----------
def to_time(iso):
    """'2026-11-17T06:48' -> '6:48 AM'"""
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M").strftime("%I:%M %p").lstrip("0")

s1, s2 = st.columns(2)
s1.info(f"🌅 Sunrise: {to_time(daily['sunrise'][0])}")      
s2.warning(f"🌇 Sunset: {to_time(daily['sunset'][0])}")     

# ---------- 16. MAP ----------
st.subheader("Location")
st.map(pd.DataFrame({"lat": [place["latitude"]], "lon": [place["longitude"]]}))  
# ---------- 17. FOOTER ----------
st.caption("Data: Open-Meteo API")
