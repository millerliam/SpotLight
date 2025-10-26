import os, requests, pandas as pd, streamlit as st
from datetime import date
from modules.nav import SideBarLinks

st.set_page_config(page_title="O&M Dashboard", layout="wide")
SideBarLinks()
st.title("O&M Dashboard")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def api(method: str, path: str, **kw):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=20, **kw)
        data = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

# ---- quick connectivity check ----
code, ping = api("GET", "/o_and_m/spots/metrics")
if code != 200:
    st.error(f"O&M API not reachable at {API} (got {code}). Set API_BASE_URL if needed. Details: {ping}")
    st.stop()

# -------- top metrics --------
m1, m2, m3 = st.columns(3)

with m1:
    st.subheader("Spots")
    code, data = api("GET", "/o_and_m/spots/metrics")
    if code == 200 and isinstance(data, dict):
        a,b,c = st.columns(3)
        a.metric("Total", data.get("total",0))
        b.metric("In use", data.get("in_use",0))
        c.metric("With issue", data.get("with_issue",0))
    else:
        st.error(f"Spots metrics error: {code} {data}")

with m2:
    st.subheader("Customers")
    code, data = api("GET", "/o_and_m/customers/metrics")
    if code == 200 and isinstance(data, dict):
        a,b,c = st.columns(3)
        a.metric("Total", data.get("total",0))
        b.metric("VIP", data.get("vip",0))
        c.metric("Never ordered", data.get("never_ordered",0))
        st.caption(f"Avg days since last order: {round(data.get('avg_days',0),2)}")
    else:
        st.error(f"Customers metrics error: {code} {data}")

with m3:
    st.subheader("Orders (365d)")
    code, data = api("GET", "/o_and_m/orders/metrics?period=365d")
    if code == 200 and isinstance(data, dict):
        def f(x, default=0.0):
            try:
                return float(x)
            except (TypeError, ValueError):
                return default

        a, b = st.columns(2)
        a.metric("All time total", int(f(data.get("total", 0))))
        b.metric("Avg order $", f"${f(data.get('avg_price', 0)):,.2f}")

        # show orders in the selected window if the backend gives it
        period_count = data.get("last_period") or data.get("orders_365d") or 0
        try:
            period_count = int(float(period_count))
        except Exception:
            period_count = 0
        st.caption(f"Orders in last 365 days: {period_count}")
    else:
        st.error(f"Orders metrics error: {code} {data}")

st.divider()

# -------- tabs: info & quick create --------
tab1, tab2, tab3, tab4 = st.tabs(["Spots info", "Customer accounts info", "Order info", "Quick insert"])

with tab1:
    st.subheader("Spots info (latest)")
    limit = st.slider("Limit", 10, 200, 50, 10, key="spots_limit")
    code, data = api("GET", f"/o_and_m/spots/summary?limit={limit}")
    if code == 200 and isinstance(data, list) and data:
        df = pd.DataFrame(data)
        show = [c for c in ["spotID","address","status","price","estViewPerMonth","monthlyRentCost"] if c in df.columns]
        st.dataframe(df[show], use_container_width=True, hide_index=True)
    else:
        st.info("No spots found or endpoint returned none.")

with tab2:
    st.subheader("Customer accounts info")
    limit = st.slider("Limit", 10, 200, 50, 10, key="cust_limit")
    code, data = api("GET", f"/o_and_m/customers/summary?limit={limit}")
    if code == 200 and isinstance(data, list) and data:
        df = pd.DataFrame(data)
        show = [c for c in ["cID","fName","lName","email","companyName","VIP","last_order_date","days_since_last_order"] if c in df.columns]
        st.dataframe(df[show], use_container_width=True, hide_index=True)
    else:
        st.info("No customers found or endpoint returned none.")

with tab3:
    st.subheader("Order info (recent 90d)")
    limit = st.slider("Limit", 10, 200, 50, 10, key="orders_limit")
    code, data = api("GET", f"/o_and_m/orders/summary?period=90d&limit={limit}")
    if code == 200 and isinstance(data, list) and data:
        df = pd.DataFrame(data)
        show = [c for c in ["orderID","date","total","cID"] if c in df.columns]
        st.dataframe(df[show], use_container_width=True, hide_index=True)
    else:
        st.info("No orders in period or endpoint returned none.")

with tab4:
    st.subheader("Quick insert")
    sub = st.segmented_control("Entity", ["Spot","Customer","Order"], key="ins_seg")

    if sub == "Spot":
        col = st.columns(3)
        price = col[0].number_input("price", 0, 10_000, 500)
        contactTel = col[1].text_input("contactTel", "000-000-0000")
        address = col[2].text_input("address", "123 Main St, Gainesville, FL")
        more = st.expander("Optional fields")
        with more:
            status = st.selectbox("status", ["free","inuse","planned","w.issue"], index=0)
            imageURL = st.text_input("imageURL", "")
            estViewPerMonth = st.number_input("estViewPerMonth", 0, 10_000_000, 1000)
            monthlyRentCost = st.number_input("monthlyRentCost", 0, 10_000, 0)
            endTimeOfCurrentOrder = st.text_input("endTimeOfCurrentOrder", "")
            latitude = st.number_input("latitude", value=29.6516, format="%.6f")
            longitude = st.number_input("longitude", value=-82.3248, format="%.6f")
        if st.button("Create spot", type="primary"):
            payload = {
                "entity":"spot","price":int(price),"contactTel":contactTel,"address":address,
                "status":status,"imageURL":imageURL or None,"estViewPerMonth":int(estViewPerMonth),
                "monthlyRentCost":int(monthlyRentCost),"endTimeOfCurrentOrder":endTimeOfCurrentOrder or None,
                "latitude":float(latitude),"longitude":float(longitude)
            }
            code, data = api("POST", "/o_and_m/insert", json=payload)
            st.success(data) if code in (200,201) else st.error(f"{code} {data}")

    if sub == "Customer":
        col = st.columns(3)
        fName = col[0].text_input("fName","Liam")
        lName = col[1].text_input("lName","Miller")
        email = col[2].text_input("email","liam@example.com")
        more = st.expander("Optional fields")
        with more:
            position = st.text_input("position","Analyst")
            companyName = st.text_input("companyName","Skyvu")
            totalOrderTimes = st.number_input("totalOrderTimes",0,1000,0)
            VIP = st.checkbox("VIP", False)
            avatarURL = st.text_input("avatarURL","")
            balance = st.number_input("balance",0,1_000_000,0)
            TEL = st.text_input("TEL","")
        if st.button("Create customer", type="primary"):
            payload = {
                "entity":"customer","fName":fName,"lName":lName,"email":email,
                "position":position or None,"companyName":companyName or None,"totalOrderTimes":int(totalOrderTimes),
                "VIP":bool(VIP),"avatarURL":avatarURL or None,"balance":int(balance),"TEL":TEL or None
            }
            code, data = api("POST", "/o_and_m/insert", json=payload)
            st.success(data) if code in (200,201) else st.error(f"{code} {data}")

    if sub == "Order":
        col = st.columns(3)
        date_str = col[0].text_input("date (YYYY-MM-DD)", str(date.today()))
        total_amt = col[1].number_input("total", 0, 1_000_000, 0)
        cID = col[2].number_input("cID (customer id)", 1, 999999, 1)
        if st.button("Create order", type="primary"):
            payload = {"entity":"order","date":date_str,"total":int(total_amt),"cID":int(cID)}
            code, data = api("POST", "/o_and_m/insert", json=payload)
            st.success(data) if code in (200,201) else st.error(f"{code} {data}")
