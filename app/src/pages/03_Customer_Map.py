#03_Customer_Map

import os
import requests
import pandas as pd
import streamlit as st
import pydeck as pdk

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000")

# ---- Map defaults (Gainesville, FL) ----
DEFAULT_CITY = "Gainesville, FL"
DEFAULT_LAT  = 29.6516
DEFAULT_LNG  = -82.3248
DEFAULT_ZOOM = 12

def api_get(path: str, **kw):
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    try:
        r = requests.get(url, timeout=15, **kw)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error for GET {url}: {e}")
        return []

st.set_page_config(page_title="Customer Map", page_icon="🗺️", layout="wide")
st.title("🗺️ Customer Map — Gainesville, FL")

# ---- Customer sidebar (shared) ----
from modules.nav import SideBarLinks
SideBarLinks()


# Controls
col1, col2, col3 = st.columns([1,1,2])
with col1:
    status = st.selectbox("Spot status", ["any","free","inuse","planned","w.issue"], index=0)
with col2:
    radius_km = st.slider("Radius (km)", 1, 20, 8)
with col3:
    st.caption("Center fixed at Gainesville, FL (29.6516, -82.3248)")
lat0, lng0 = 29.6516, -82.3248

# Fetch spots from your salesman search endpoint
params = f"lat={lat0}&lng={lng0}&radius_km={radius_km}"
if status != "any":
    params += f"&status={status}"

data = api_get(f"/salesman/spots?{params}")

if not isinstance(data, list) or len(data) == 0:
    st.info("No spots returned. Try a larger radius or different status.")
    st.stop()

df = pd.DataFrame(data).rename(columns={"latitude":"lat","longitude":"lng"})
# make sure required columns exist
needed = {"lat","lng","address","spotID"}
missing = needed - set(df.columns)
if missing:
    st.error(f"API response missing required columns: {missing}")
    st.stop()

# Map
layer = pdk.Layer(
    "ScatterplotLayer",
    df,
    get_position="[lng, lat]",
    get_radius=60,
    pickable=True,
)
view_state = pdk.ViewState(latitude=lat0, longitude=lng0, zoom=12)
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_provider="carto",
        map_style="light",        
        tooltip={"text": "{address}\nstatus: {status}"}
    )
)

# Table
st.divider()
st.caption(f"{len(df)} spots found")
cols = [c for c in ["spotID","address","lat","lng","status","distance_km"] if c in df.columns]
st.dataframe(df[cols], use_container_width=True, hide_index=True)
