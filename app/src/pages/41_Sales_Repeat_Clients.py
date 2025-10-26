# 41_Sales_Repeat_Clients.py
import os, sys, requests, pandas as pd, streamlit as st
from datetime import date

# Sidebar helper
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from modules.nav import SideBarLinks

st.set_page_config(page_title="Sales • Repeat Clients", page_icon="🔁", layout="wide")
SideBarLinks()
st.title("🔁 Repeat Clients & Quick Renewals")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def api(method, path, **kw):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=25, **kw)
        data = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

def fnum(x, d=0.0):
    try: return float(x)
    except: return float(d)

# Pull 2 years of orders to find repeats
oc, od = api("GET", "/o_and_m/orders/summary?period=730d&limit=100000")
dfO = pd.DataFrame(od) if (oc == 200 and isinstance(od, list)) else pd.DataFrame()

if dfO.empty or not {"cID","date","total"}.issubset(dfO.columns):
    st.info("Orders data not available yet.")
    st.stop()

dfO["date"] = pd.to_datetime(dfO["date"], errors="coerce")
last = dfO.sort_values("date").groupby("cID").tail(1)[["cID","date","total"]]
cnt  = dfO.groupby("cID").size().rename("orders_2y").reset_index()
sp   = dfO.groupby("cID")["total"].sum().rename("spend_2y").reset_index()
df   = cnt.merge(last, on="cID", how="left").merge(sp, on="cID", how="left")
df["last_total"] = df["total"].apply(fnum); df.drop(columns=["total"], inplace=True)

st.subheader("Top repeat clients")
min_orders = st.slider("Min orders (2y)", 2, 10, 2)
top = df[df["orders_2y"] >= min_orders].sort_values(["orders_2y","spend_2y"], ascending=[False,False]).head(200)
# best-effort names (only for visible rows)
names = {}
for cid in top["cID"].tolist():
    nc, ndata = api("GET", f"/customer/{int(cid)}")
    if nc == 200 and isinstance(ndata, dict):
        nm = f"{ndata.get('fName','')} {ndata.get('lName','')}".strip()
        if ndata.get("companyName"): nm = f"{nm} ({ndata.get('companyName')})" if nm else ndata.get("companyName")
    else:
        nm = f"Customer {cid}"
    names[cid] = nm
top = top.assign(customer=top["cID"].map(names))
show = top[["customer","cID","orders_2y","date","last_total","spend_2y"]].rename(columns={"date":"last_order_date"})
show["last_total"] = show["last_total"].map(lambda x: f"${x:,.0f}")
show["spend_2y"]   = show["spend_2y"].map(lambda x: f"${fnum(x):,.0f}")
st.dataframe(show, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Quick same-price renewal")
colA, colB = st.columns([1,1])
with colA:
    rcid = st.number_input("cID", 1, 999999, 1)
with colB:
    same = df.loc[df["cID"] == int(rcid), "last_total"]
    amt = int(same.iloc[0]) if len(same) else 500
    amt = st.number_input("Renewal total ($)", 0, 1_000_000, amt)
if st.button("Create renewal order", type="primary"):
    body = {"entity":"order","date":str(date.today()),"total":int(amt),"cID":int(rcid)}
    pc, pd = api("POST", "/o_and_m/insert", json=body)
    st.success(pd) if pc in (200,201) else st.error(f"{pc} {pd}")
