import os, requests, pandas as pd, streamlit as st
from modules.nav import SideBarLinks



st.set_page_config(page_title="O&M Statistics", layout="wide")
SideBarLinks()
st.title("Statistics")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def api(method: str, path: str, **kw):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=20, **kw)
        data = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

period = st.segmented_control("Period", ["90d", "180d", "365d", "730d"], default="365d")
st.caption("Metrics use the selected period where applicable (orders).")

c1, c2, c3 = st.columns(3)

with c1:
    st.subheader("Spots")
    code, data = api("GET", "/o_and_m/spots/metrics")
    if code == 200 and isinstance(data, dict):
        a,b,c = st.columns(3)
        a.metric("Total", data.get("total",0))
        b.metric("In use", data.get("in_use",0))
        c.metric("With issue", data.get("with_issue",0))
    else:
        st.error(f"{code} {data}")

with c2:
    st.subheader("Customers")
    code, data = api("GET", "/o_and_m/customers/metrics")
    if code == 200 and isinstance(data, dict):
        a,b,c = st.columns(3)
        a.metric("Total", data.get("total",0))
        b.metric("VIP", data.get("vip",0))
        c.metric("Never ordered", data.get("never_ordered",0))
        st.caption(f"Avg days since last order: {round(data.get('avg_days',0),2)}")
    else:
        st.error(f"{code} {data}")

with c3:
    st.subheader("Orders")
    code, data = api("GET", f"/o_and_m/orders/metrics?period={period}")
    if code == 200 and isinstance(data, dict):
        def f(x, default=0.0):
            try:
                return float(x)
            except (TypeError, ValueError):
                return default

        a, b = st.columns(2)
        a.metric("All time total", int(f(data.get("total", 0))))
        b.metric("Avg order $", f"${f(data.get('avg_price', 0)):,.2f}")

        # optional caption: how many orders in the chosen window
        period_count = data.get("last_period") or data.get(f"orders_{period}") or 0
        try:
            period_count = int(float(period_count))
        except Exception:
            period_count = 0
        st.caption(f"Orders in {period}: {period_count}")
    else:
        st.error(f"{code} {data}")


st.divider()
t1, t2, t3 = st.tabs(["Recent spots", "Recent customers", "Recent orders"])

with t1:
    code, data = api("GET", "/o_and_m/spots/summary?limit=25")
    if code == 200 and isinstance(data, list) and data:
        df = pd.DataFrame(data)
        show = [c for c in ["spotID","address","status","price","estViewPerMonth","monthlyRentCost"] if c in df.columns]
        st.dataframe(df[show], use_container_width=True, hide_index=True)
    else:
        st.info("No data.")

with t2:
    code, data = api("GET", "/o_and_m/customers/summary?limit=25")
    if code == 200 and isinstance(data, list) and data:
        df = pd.DataFrame(data)
        show = [c for c in ["cID","fName","lName","email","companyName","VIP","last_order_date","days_since_last_order"] if c in df.columns]
        st.dataframe(df[show], use_container_width=True, hide_index=True)
    else:
        st.info("No data.")

with t3:
    code, data = api("GET", f"/o_and_m/orders/summary?period={period}&limit=25")
    if code == 200 and isinstance(data, list) and data:
        df = pd.DataFrame(data)
        show = [c for c in ["orderID","date","total","cID"] if c in df.columns]
        st.dataframe(df[show], use_container_width=True, hide_index=True)
    else:
        st.info("No data.")
