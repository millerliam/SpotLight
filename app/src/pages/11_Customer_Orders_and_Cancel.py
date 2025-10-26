#11_Customer_Orders_and_Cancel.py
import os, requests, pandas as pd, streamlit as st

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000")

def api(method, path, **kw):
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=15, **kw)
        ct = r.headers.get("content-type","")
        data = r.json() if "application/json" in ct else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

st.set_page_config(page_title="Customer – Orders", page_icon="🧾", layout="wide")
st.title("🧾 Orders & Cancellations")

# ---- Customer sidebar (shared) ----
from modules.nav import SideBarLinks
SideBarLinks()


# Pick a customer
code, customers = api("GET", "/customer/")
if code != 200 or not isinstance(customers, list) or len(customers)==0:
    st.error("Could not load customers from /customer/.")
    st.stop()

cust_options = {f"{c['cID']} — {c.get('fName','')} {c.get('lName','')} <{c.get('email','')}>": c for c in customers}
labels = list(cust_options.keys())

default_idx = 0
if "cID" in st.session_state:
    for i, lbl in enumerate(labels):
        if cust_options[lbl]["cID"] == st.session_state["cID"]:
            default_idx = i
            break

cust_label = st.selectbox("Select customer", labels, index=default_idx)
cust = cust_options[cust_label]
cID = cust["cID"]

# existing
oc, odata = api("GET", f"/customer/{cID}/orders")
if oc != 200 or not isinstance(odata, list): ...
df = pd.DataFrame(odata)

# NEW: pull paid/unpaid info
tcode, tdata = api("GET", "/to_be_processed_order")  # unpaid/open
pcode, pdata = api("GET", "/processed_orders")       # paid

open_ids = set([row["orderID"] for row in tdata]) if tcode == 200 and isinstance(tdata, list) else set()
paid_ids = set([row["orderID"] for row in pdata]) if pcode == 200 and isinstance(pdata, list) else set()

def label_status(oid: int) -> str:
    if oid in open_ids: return "UNPAID"
    if oid in paid_ids: return "PAID"
    return "UNKNOWN"  # e.g., created but not queued, or data gap

df["paymentStatus"] = df["orderID"].map(label_status)

cols = [c for c in ["orderID","date","total","paymentStatus","cID"] if c in df.columns]
st.dataframe(df[cols], use_container_width=True, hide_index=True)


# Load orders
oc, odata = api("GET", f"/customer/{cID}/orders")
if oc != 200 or not isinstance(odata, list):
    st.error(f"Failed to load orders: {oc} {odata}")
    st.stop()

if not odata:
    st.info("No orders yet.")
    st.stop()

df = pd.DataFrame(odata)
cols = [c for c in ["orderID","date","total","status","cID"] if c in df.columns]
st.dataframe(df[cols], use_container_width=True, hide_index=True)

# Cancel an order
st.subheader("Cancel an unpaid order")

cancellable_ids = [oid for oid in df["orderID"].tolist() if oid in open_ids]
if not cancellable_ids:
    st.info("No unpaid (unprocessed) orders to cancel.")
else:
    oid = st.selectbox("Order to cancel", cancellable_ids)
    if st.button("❌ Cancel order"):
        dc, ddata = api("DELETE", f"/orders?orderID={oid}")
        if dc == 200:
            st.success(f"Order {oid} cancelled.")
            st.rerun()
        else:
            # if backend returned HTML, 'ddata' will be a long string; show a friendly summary
            msg = ddata if isinstance(ddata, dict) else "Server error (likely processed or has linked records)."
            st.error(f"Cancel failed {dc}: {msg}")

