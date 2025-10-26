# pages/Salesman_Workbench.py
import os
import requests
import pandas as pd
import streamlit as st

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000")

def api_get(path: str, **kw):
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    try:
        r = requests.get(url, timeout=15, **kw)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error for GET {url}: {e}")
        return []

st.set_page_config(page_title="Salesman Workbench", page_icon="💼", layout="wide")
st.title("💼 Salesman Workbench")

# ---- Salesman sidebar (shared) ----
with st.sidebar:
    st.subheader("Salesman pages")
    try:
        st.page_link("pages/10_workbench.py",     label="💼 Workbench")
        
    except Exception:
        if st.button("💼 Workbench"):      st.switch_page("pages/10_workbench.py")
       

# Controls
col1, col2, col3 = st.columns([1,1,2])
with col1:
    customer_type = st.selectbox("Customer type", ["all","vip","regular"], index=0)
with col2:
    limit = st.slider("Max results", 10, 100, 20)
with col3:
    search_query = st.text_input("Search customers", placeholder="Name, email, or company...")

# Fetch customers data
params = f"limit={limit}"
if search_query:
    params = f"q={search_query}"

data = api_get(f"/customer/?{params}")

if not isinstance(data, list) or len(data) == 0:
    st.info("No customers found. Try adjusting your search or filters.")
    st.stop()

# Filter by customer type
if customer_type == "vip":
    data = [c for c in data if c.get("VIP")]
elif customer_type == "regular":
    data = [c for c in data if not c.get("VIP")]

df = pd.DataFrame(data)

# Ensure we have the basic columns we need
needed = {"cID", "fName", "lName", "email"}
missing = needed - set(df.columns)
if missing:
    st.error(f"API response missing required columns: {missing}")
    st.stop()

# Add full name column for easier display
if "fName" in df.columns and "lName" in df.columns:
    df["fullName"] = df["fName"].fillna("") + " " + df["lName"].fillna("")

# Customer cards display
st.divider()
st.caption(f"{len(df)} customers found")

for _, customer in df.iterrows():
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            st.write(f"**{customer.get('fullName', 'N/A')}**")
            if customer.get('VIP'):
                st.markdown("🌟 VIP")
            st.caption(f"ID: {customer.get('cID', 'N/A')}")
        
        with col2:
            st.write(f"📧 {customer.get('email', 'N/A')}")
            if customer.get('companyName'):
                st.write(f"🏢 {customer.get('companyName')}")
        
        with col3:
            if customer.get('TEL'):
                st.write(f"📞 {customer.get('TEL')}")
                st.link_button("Call", f"tel:{str(customer.get('TEL')).replace(' ', '')}", 
                             key=f"call_{customer.get('cID')}", use_container_width=True)
            else:
                st.write("📞 No phone")
        
        with col4:
            st.write(f"**Orders:** {customer.get('totalOrderTimes', 0)}")
            if st.button("View", key=f"view_{customer.get('cID')}"):
                st.info(f"View details for customer {customer.get('cID')}")

# Summary table
st.divider()
st.caption("Customer Summary")
display_cols = []
for col in ["cID", "fullName", "email", "companyName", "VIP", "totalOrderTimes", "TEL"]:
    if col in df.columns:
        display_cols.append(col)

st.dataframe(df[display_cols], use_container_width=True, hide_index=True)