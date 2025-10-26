# pages/42_Sales_Spots.py
import os, sys, requests, pandas as pd, streamlit as st

# Sidebar helper
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from modules.nav import SideBarLinks

st.set_page_config(page_title="Sales • Spots", page_icon="📍", layout="wide")
SideBarLinks()
st.title("📍 Spots — addresses & issue flagging")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def api(method, path, **kw):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=25, **kw)
        data = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

# Load spots (O&M summary gives all)
code, data = api("GET", "/o_and_m/spots/summary?limit=10000")
if code != 200 or not isinstance(data, list):
    st.error(f"Failed to load spots: {code} {data}")
    st.stop()
df = pd.DataFrame(data).rename(columns={"latitude":"lat","longitude":"lng"})
if df.empty:
    st.info("No spots found.")
    st.stop()

# Filters
c1, c2, c3 = st.columns([2,1,1])
with c1: q = st.text_input("Search (address/company/ID)")
with c2: status = st.selectbox("Status", ["any","free","inuse","planned","w.issue"], index=0)
with c3: limit = st.slider("Show up to", 10, 2000, 500, 10)

mask = pd.Series([True]*len(df))
if q.strip():
    needle = q.strip().lower()
    cols = [c for c in ["address","companyName","spotID"] if c in df.columns]
    def hit(row):
        for c in cols:
            if needle in str(row.get(c,"")).lower(): return True
        return False
    mask = df.apply(hit, axis=1)
if status != "any" and "status" in df.columns:
    mask = mask & (df["status"] == status)

view = df.loc[mask].copy().head(limit)
show = [c for c in ["spotID","address","status","price","estViewPerMonth","contactTel","lat","lng"] if c in view.columns]
st.dataframe(view[show], use_container_width=True, hide_index=True)

st.divider()
st.subheader("Quick actions")

colA, colB, colC = st.columns([1,1,2])
with colA:
    sid = st.number_input("spotID", 1, 999999, int(view.iloc[0]["spotID"]) if not view.empty else 1)
with colB:
    if st.button("Mark w.issue", type="primary"):
        c, d = api("PUT", f"/salesman/spots/{int(sid)}/status", json={"status":"w.issue"})
        st.success(d) if c in (200,204) else st.error(f"{c} {d}")
with colC:
    st.caption("Use search above to find a spot, then mark it **w.issue** if there’s a problem.")

st.divider()
st.subheader("Assign spot to a customer (optional)")
col1, col2 = st.columns([1,2])
with col1:
    cid = st.number_input("cID", 1, 999999, 1)
with col2:
    if st.button("Assign"):
        # try an owner/salesman endpoint first; fall back to O&M insert
        c, d = api("POST", "/salesman/assign", json={"spotID": int(sid), "cID": int(cid)})
        if c not in (200,201):
            c, d = api("POST", "/o_and_m/insert", json={"entity":"spot_assignment","spotID":int(sid),"cID":int(cid)})
        st.success(d) if c in (200,201) else st.error(f"{c} {d}")
