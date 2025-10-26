# 40_Sales_Leads.py
import os, sys, requests, pandas as pd, streamlit as st

# Sidebar helper
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from modules.nav import SideBarLinks

st.set_page_config(page_title="Sales • Leads", page_icon="📇", layout="wide")
SideBarLinks()
st.title("📇 Inbound Leads Queue")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def api(method, path, **kw):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=20, **kw)
        data = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

# --- Create (intake) a lead (simple form) ---
st.subheader("New inbound lead")
c1, c2, c3 = st.columns([2,2,1])
with c1: name = st.text_input("Business / Contact")
with c2: phone = st.text_input("Phone")
with c3: region = st.text_input("Region", "Gainesville")
addr = st.text_input("Address (street, city, state)")
if st.button("Add to pending queue", type="primary"):
    body = {"name": name, "phone": phone, "address": addr, "region": region, "status": "pending"}
    code, data = api("POST", "/salesman/leads", json=body)
    if code not in (200,201):
        # fallback to O&M insert
        code, data = api("POST", "/o_and_m/insert", json={"entity":"lead", **body})
    st.success("Lead added.") if code in (200,201) else st.error(f"{code} {data}")

st.divider()

# --- Pending list + quick status updates ---
st.subheader("Pending inquiries")
c1, c2 = st.columns([2,1])
with c1: q = st.text_input("Search (name/phone/address)")
with c2: limit = st.slider("Show up to", 10, 1000, 200, 10)

qs = f"status=pending&limit={limit}"
if q.strip(): qs += f"&q={requests.utils.quote(q.strip())}"
code, data = api("GET", f"/salesman/leads?{qs}")
if code != 200 or not isinstance(data, list):
    st.info("No /salesman/leads endpoint — showing nothing until API is wired.")
else:
    df = pd.DataFrame(data)
    if df.empty:
        st.info("No pending leads.")
    else:
        keep = [c for c in ["leadID","name","phone","address","region","created_at","decline_count","notes"] if c in df.columns]
        st.dataframe(df[keep] if keep else df, use_container_width=True, hide_index=True)

        st.subheader("Quick actions")
        colA, colB, colC, colD = st.columns(4)
        with colA: lid = st.number_input("leadID", 1, 999999, 1)
        with colB:
            if st.button("Mark called"):
                c, d = api("PUT", f"/salesman/leads/{int(lid)}", json={"status":"called"})
                st.success(d) if c == 200 else st.error(f"{c} {d}")
        with colC:
            if st.button("Mark invalid"):
                c, d = api("PUT", f"/salesman/leads/{int(lid)}", json={"status":"invalid"})
                if c == 404:
                    # fallback record
                    c, d = api("POST", "/o_and_m/insert", json={"entity":"lead_update","leadID":int(lid),"status":"invalid"})
                st.success(d) if c in (200,201) else st.error(f"{c} {d}")
        with colD:
            reason = st.text_input("Note (optional)")
            if st.button("Declined this call"):
                c, d = api("PUT", f"/salesman/leads/{int(lid)}", json={"status":"declined","notes":reason})
                st.success(d) if c == 200 else st.error(f"{c} {d}")
