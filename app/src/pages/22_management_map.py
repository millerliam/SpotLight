import os, requests, pandas as pd, streamlit as st, pydeck as pdk
from modules.nav import SideBarLinks

st.set_page_config(page_title="O&M Spots Manager", layout="wide")
SideBarLinks()
st.title("O&M Spots Dashboard")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def api(method: str, path: str, **kw):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=20, **kw)
        data = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

# Gainesville defaults
DEFAULT_LAT, DEFAULT_LNG, DEFAULT_ZOOM = 29.6516, -82.3248, 12

# ----- filters -----
left, right = st.columns([1,3])
with left:
    status = st.selectbox("Status", ["any","free","inuse","planned","w.issue"], index=0)
    radius_km = st.slider("Radius (km)", 1, 20, 8)
    lat0 = st.number_input("Center lat", value=DEFAULT_LAT, format="%.6f")
    lng0 = st.number_input("Center lng", value=DEFAULT_LNG, format="%.6f")
    if st.button("Center on Gainesville"):
        lat0, lng0 = DEFAULT_LAT, DEFAULT_LNG
with right:
    st.caption("Use filters to fetch nearby spots. Click a point to see details in the table below.")

params = f"lat={lat0}&lng={lng0}&radius_km={radius_km}" + (f"&status={status}" if status != "any" else "")
code, data = api("GET", f"/salesman/spots?{params}")
if code != 200 or not isinstance(data, list):
    st.error(f"Failed to load spots: {code} {data}")
    st.stop()

df = pd.DataFrame(data).rename(columns={"latitude":"lat","longitude":"lng"})
if df.empty:
    st.info("No spots returned for those filters.")
    st.stop()

# ----- map (force light basemap) -----
layer = pdk.Layer("ScatterplotLayer", df, get_position="[lng, lat]", get_radius=60, pickable=True)
view_state = pdk.ViewState(latitude=float(lat0), longitude=float(lng0), zoom=DEFAULT_ZOOM)
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_provider="carto",
        map_style="light",
        tooltip={"text": "{address}\nstatus: {status}"},
    )
)

# ----- table & quick status update -----
st.caption(f"{len(df)} spot(s) found")
show_cols = [c for c in ["spotID","address","lat","lng","status","price","estViewPerMonth","monthlyRentCost","contactTel","distance_km"] if c in df.columns]
st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

st.subheader("Update spot status")
sid = st.number_input("spotID", min_value=1, step=1, value=int(df.iloc[0]["spotID"]))
new_status = st.selectbox("New status", ["free","inuse","planned","w.issue"], index=0)
if st.button("Update status", type="primary"):
    code, resp = api("PUT", f"/salesman/spots/{int(sid)}/status", json={"status": new_status})
    if code in (200,204):
        st.success(f"Updated spot {int(sid)} to {new_status}. Refresh the list above to see it.")
    else:
        st.error(f"Update failed: {code} {resp}")
