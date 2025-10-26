# 10_Customer_Browse_and_Cart.py

import os, time, json, requests, pandas as pd, streamlit as st, pydeck as pdk
from datetime import date

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000")

# ---- Map defaults (Gainesville, FL) ----
DEFAULT_CITY = "Gainesville, FL"
DEFAULT_LAT  = 29.6516
DEFAULT_LNG  = -82.3248
DEFAULT_ZOOM = 12

def api(method, path, **kw):
    url = f"{API.rstrip('/')}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=20, **kw)
        ct = r.headers.get("content-type","")
        data = r.json() if "application/json" in ct else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

st.set_page_config(page_title="Customer – Browse & Cart", page_icon="🛒", layout="wide")
st.title("🛒 Browse Spots & Build Your Order")

# ---- Customer sidebar (shared) ----
from modules.nav import SideBarLinks
SideBarLinks()

# --- session cart ---
if "cart" not in st.session_state:
    st.session_state.cart = {}  # {spotID: row_dict}

# --- pick a customer ---
st.subheader("1) Who is ordering?")
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

# --- browse spots (map + table) ---

st.subheader("2) Browse & filter spots (Gainesville default center)")
c1, c2, c3, c4 = st.columns([1,1,1,2])
with c1:
    status = st.selectbox("Status", ["any","free","inuse","planned","w.issue"], index=0)
with c2:
    radius_km = st.slider("Radius (km)", 1, 20, 8)
with c3:
    lat0 = st.number_input("Center lat", value=29.6516, format="%.5f")
with c4:
    lng0 = st.number_input("Center lng", value=-82.3248, format="%.5f")

params = f"lat={lat0}&lng={lng0}&radius_km={radius_km}"
if status != "any":
    params += f"&status={status}"

code, spotdata = api("GET", f"/salesman/spots?{params}")
if code != 200 or not isinstance(spotdata, list):
    st.error(f"Failed to load spots: {spotdata}")
    st.stop()

df = pd.DataFrame(spotdata).rename(columns={"latitude": "lat", "longitude": "lng"})
if df.empty:
    st.info("No spots returned with those filters.")
else:
    # --- Map (forced light basemap) ---
    layer = pdk.Layer(
        "ScatterplotLayer",
        df,
        get_position="[lng, lat]",
        get_radius=60,
        pickable=True,
    )
    view_state = pdk.ViewState(latitude=float(lat0), longitude=float(lng0), zoom=12)

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_provider="carto",  
            map_style="light",      # <-- force light mode
            tooltip={"text": "{address}\nstatus: {status}"},
        )
    )

    st.caption(f"{len(df)} spot(s) found")
    show_cols = [c for c in ["spotID","address","lat","lng","status","price","estViewPerMonth","distance_km"] 
                 if c in df.columns]
    st.dataframe(df[show_cols], use_container_width=True, hide_index=True)


# --- add/remove cart ---
st.subheader("3) Add / remove spots")
colL, colR = st.columns([2,1])

with colL:
    try:
        spot_ids = df["spotID"].tolist()
    except Exception:
        spot_ids = []
    add_id = st.selectbox("Add spotID to cart", spot_ids if spot_ids else [None])
    if st.button("➕ Add to cart", disabled=(not spot_ids)):
        row = df[df["spotID"] == add_id].iloc[0].to_dict()
        st.session_state.cart[add_id] = row
        st.success(f"Added spot {add_id}")

    # remove
    if st.session_state.cart:
        rem_id = st.selectbox("Remove from cart", list(st.session_state.cart.keys()))
        if st.button("➖ Remove selected"):
            st.session_state.cart.pop(rem_id, None)
            st.info(f"Removed {rem_id}")

with colR:
    st.write("Cart summary")

    cart_rows = list(st.session_state.cart.values())
    n = len(cart_rows)

    total_price = sum((r.get("price") or 0) for r in cart_rows)
    total_views = sum((r.get("estViewPerMonth") or 0) for r in cart_rows)

    # Always show metrics (they’ll be 0 when empty)
    st.metric("Spots selected", n)
    st.metric("Estimated price (sum)", f"${total_price:,.2f}")
    st.metric("Est. monthly views (sum)", f"{total_views:,}")

    # Only render the per-item table when cart has items
    if cart_rows:
        all_keys = set().union(*(row.keys() for row in cart_rows))
        show_cols = [c for c in ["spotID", "address", "price", "estViewPerMonth"] if c in all_keys]
        st.dataframe(
            pd.DataFrame.from_records(cart_rows)[show_cols],
            hide_index=True,
            use_container_width=True,
        )


# --- place order ---
st.subheader("4) Place order")
with st.form("place_order"):
    order_date = st.date_input("End date (order expiry)", value=date.today())
    submitted = st.form_submit_button("🧾 Place Order", disabled=(len(st.session_state.cart)==0))

if submitted:
    # 4a) create order
    payload = {"cID": int(cID), "total": float(total_price), "date": str(order_date)}
    oc, odata = api("POST", "/orders", json=payload)
    if oc not in (200,201):
        st.error(f"Failed to create order via POST /orders. Response: {oc} {odata}")
        st.stop()

    # try to find orderID in response; fallback: pick latest customer order
    order_id = None
    if isinstance(odata, dict):
        for k in ("orderID","id","created_id","createdId"):
            if k in odata:
                order_id = odata[k]
                break
    if not order_id:
        # fallback—take most recent order for this customer
        gc, gdata = api("GET", f"/customer/{cID}/orders")
        if gc == 200 and isinstance(gdata, list) and len(gdata):
            # assume highest/last is newest
            order_id = sorted([row.get("orderID") for row in gdata if "orderID" in row])[-1]

    if not order_id:
        st.error("Order created but could not determine orderID from API response. Please verify your POST /orders returns orderID.")
        st.stop()

    # 4b) attach spots
    failures = []
    for sid in list(st.session_state.cart.keys()):
        pc, pdata = api("POST", f"/salesman/spotorders/{sid}/{order_id}")
        if pc not in (200,201):
            failures.append({"spotID": sid, "code": pc, "resp": pdata})

    if failures:
        st.warning(f"Order {order_id} created, but some spots failed to attach.")
        st.json(failures)
    else:
        st.success(f"Order {order_id} created with {len(st.session_state.cart)} spot(s)!")
        # clear cart after success
        st.session_state.cart = {}
        time.sleep(0.5)
        st.rerun()
