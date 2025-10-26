#01_Customer_Profile.py
import os, requests, streamlit as st
from datetime import date

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

st.set_page_config(page_title="Customer Profile", page_icon="👤", layout="wide")
st.title("👤 Customer Profile")

# ---- Quick nav to other Customer pages ----
from modules.nav import SideBarLinks
SideBarLinks()
            
# --- list / search ---
col_a, col_b = st.columns([2,1])
with col_a:
    q = st.text_input("Search customers (name/email)", "")
with col_b:
    if st.button("Refresh"):
        pass

code, data = api("GET", f"/customer/?q={q}") if q else api("GET", "/customer/")
if code != 200 or isinstance(data, dict) and data.get("error"):
    st.error(f"Failed to load customers: {data}")
    st.stop()

rows = data if isinstance(data, list) else []
if not rows:
    st.info("No customers found.")
    st.stop()

# pick one
options = {f"{r['cID']} — {r.get('fName','')} {r.get('lName','')}  <{r.get('email','')}>": r for r in rows}
label = st.selectbox("Select a customer", list(options.keys()))
cust = options[label]

# Fetch this customer's orders ONCE
oc, orders_data = api("GET", f"/customer/{cust['cID']}/orders")
orders = orders_data if (oc == 200 and isinstance(orders_data, list)) else []

st.subheader("Account")

# Current balance
current_balance = cust.get("balance", 0.0) or 0.0
st.write(f"**Balance:** ${current_balance:,.2f}")

# Current Monthly Spend: sum totals for active orders (today <= end date)
active_total = 0.0
today = date.today()
for o in orders:
    end_str = o.get("date")  # end date per your schema
    if end_str:
        try:
            if date.fromisoformat(end_str) >= today and (o.get("total") is not None):
                active_total += float(o["total"])
        except Exception:
            pass

st.write(f"**Current Monthly Spend:** ${active_total:,.2f}")

st.divider()
st.write("### Add Funds")

# Optional: use a form to avoid re-running on every widget interaction
with st.form("add_funds_form", clear_on_submit=True):
    amount = st.number_input("Amount to add", min_value=1.0, step=1.0, value=10.0)
    submitted = st.form_submit_button("Add")
    if submitted:
        pc, pdata = api("POST", f"/customer/{cust['cID']}/funds", json={"amount": float(amount)})
        if pc == 200 and isinstance(pdata, dict):
            st.success(f"Funds added. New balance: ${pdata.get('balance', 0):,.2f}")
            st.rerun()
        else:
            st.error(f"Add funds failed ({pc}): {pdata}")

st.divider()
st.write("### Delete Customer")

# Guard delete to avoid FK error
if orders:
    st.info("This customer has orders and cannot be deleted.")
    st.button("Delete Customer", disabled=True)
else:
    if st.button("Delete Customer"):
        dc, dresp = api("DELETE", f"/customer/{cust['cID']}")
        if dc == 200:
            st.success("Customer deleted.")
            st.rerun()
        else:
            st.error(f"Delete failed ({dc}): {dresp}")

left, right = st.columns(2)

with left:
    st.subheader("Details")
    st.json(cust, expanded=False)

    st.subheader("Orders")
    # Reuse the 'orders' we already fetched
    if orders:
        st.dataframe(orders, hide_index=True, use_container_width=True)
    else:
        if oc == 200:
            st.info("No orders found.")
        else:
            st.warning(f"Could not load orders: {orders_data}")

with right:
    st.subheader("Actions")
    st.write("Use the controls above to add funds or delete the customer.")
    # IMPORTANT: Do NOT add another delete button here unless it respects the same guard.
