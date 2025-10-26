# 30_Owner_Home.py
import os, sys, requests, pandas as pd, streamlit as st

# --- Sidebar helper (import from modules/nav.py) ---
from modules.nav import SideBarLinks

st.set_page_config(page_title="Owner • Dashboard", page_icon="📊", layout="wide")
SideBarLinks()
st.title("📊 Owner Dashboard")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def api(method: str, path: str, **kw):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=25, **kw)
        data = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

# -------- helpers to safely coerce numbers (API sometimes returns strings) --------
def fnum(x, default=0.0):
    try:    return float(x)
    except: return float(default)

def fint(x, default=0):
    try:    return int(float(x))
    except: return int(default)

# ---- Try /owner/overview; fallback to O&M metrics if not present ----
code, overview = api("GET", "/owner/overview")
if code != 200 or not isinstance(overview, dict):
    overview = {}
    sc, s = api("GET", "/o_and_m/spots/metrics")
    cc, c = api("GET", "/o_and_m/customers/metrics")
    oc, o = api("GET", "/o_and_m/orders/metrics?period=90d")
    if sc == 200 and isinstance(s, dict):
        overview.update({
            "spots_total": s.get("total", 0),
            "spots_in_use": s.get("in_use", 0),
            "spots_with_issue": s.get("with_issue", 0),
        })
    if cc == 200 and isinstance(c, dict):
        overview.update({"vip_count": c.get("vip", 0)})
    if oc == 200 and isinstance(o, dict):
        # allow either field name the backend might provide
        overview.update({
            "revenue_90d": o.get("sum_total", o.get("last_period_total", 0)),
            "avg_order_value": o.get("avg_price", 0),
        })

# -------- KPI cards (string-safe) --------
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Spots",    fint(overview.get("spots_total", 0)))
k2.metric("In Use",         fint(overview.get("spots_in_use", 0)))
k3.metric("With Issue",     fint(overview.get("spots_with_issue", 0)))
k4.metric("VIP Customers",  fint(overview.get("vip_count", 0)))
k5.metric("Revenue (90d)",  f"${fnum(overview.get('revenue_90d', 0)):,.0f}")
k6.metric("Avg Order $",    f"${fnum(overview.get('avg_order_value', 0)):,.2f}")

st.divider()

# ---- Region heat (preferred Owner API; graceful fallback text) ----
st.subheader("Regions — spots, in-use %, revenue (90d)")
rc, rdata = api("GET", "/owner/regions/rollup?period=90d")
if rc == 200 and isinstance(rdata, list) and rdata:
    df_regions = pd.DataFrame(rdata)
    want = [c for c in ["region","spots_total","in_use_pct","revenue_90d","orders_90d","views_90d"] if c in df_regions.columns]
    st.dataframe(df_regions[want], use_container_width=True, hide_index=True)
else:
    st.info("Region rollup not available yet. Add /owner/regions/rollup or extend O&M summaries.")

st.divider()

# ---- Top lists ----
cA, cB = st.columns(2)

with cA:
    st.subheader("Top 10 Clients by Spend (90d)")
    oc, odata = api("GET", "/o_and_m/orders/summary?period=90d&limit=10000")
    if oc == 200 and isinstance(odata, list) and odata:
        df = pd.DataFrame(odata)
        if {"cID","total"}.issubset(df.columns):
            top = (df.groupby("cID")["total"]
                     .sum()
                     .reset_index()
                     .sort_values("total", ascending=False)
                     .head(10))
            # best-effort names
            names = {}
            for cid in top["cID"].tolist():
                nc, ndata = api("GET", f"/customer/{int(cid)}")
                if nc == 200 and isinstance(ndata, dict):
                    nm = f"{ndata.get('fName','')} {ndata.get('lName','')}".strip()
                    if ndata.get("companyName"):
                        nm = f"{nm} ({ndata.get('companyName')})" if nm else ndata.get("companyName")
                else:
                    nm = f"Customer {cid}"
                names[cid] = nm
            top["customer"] = top["cID"].map(names)
            top["total"] = top["total"].map(lambda x: f"${fnum(x):,.0f}")
            st.dataframe(top[["customer","cID","total"]], use_container_width=True, hide_index=True)
    else:
        st.info("No order data for last 90 days.")

with cB:
    st.subheader("Top 10 Regions (orders/views)")
    if rc == 200 and isinstance(rdata, list) and rdata:
        dfR = pd.DataFrame(rdata)
        if "orders_90d" in dfR.columns:
            show_orders = dfR.sort_values("orders_90d", ascending=False).head(10)[["region","orders_90d"]]
            st.markdown("**By orders (90d)**")
            st.dataframe(show_orders, use_container_width=True, hide_index=True)
        if "views_90d" in dfR.columns:
            show_views = dfR.sort_values("views_90d", ascending=False).head(10)[["region","views_90d"]]
            st.markdown("**By views (90d)**")
            st.dataframe(show_views, use_container_width=True, hide_index=True)
    else:
        st.info("Region rollup not available to rank regions yet.")

st.divider()