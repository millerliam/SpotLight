# 32_Owner_Priicing_and_Discounts.py
import os, sys, requests, json, pandas as pd, streamlit as st

# --- nav import like Customer ---
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from modules.nav import SideBarLinks

st.set_page_config(page_title="Owner • Pricing & Discounts", page_icon="💸", layout="wide")
SideBarLinks()
st.title("💸 Pricing & Discounts (Bulk)")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def api(method: str, path: str, **kw):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=30, **kw)
        data = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

# ---- Filters ----
st.subheader("Filters")
f1, f2, f3, f4 = st.columns([2,1,1,1])
with f1: regions = st.text_input("Regions (comma-sep)", "Gainesville")
with f2: status = st.selectbox("Status / Type", ["any","free","inuse","planned","w.issue"], index=0)
with f3: pmin = st.number_input("Min price", 0, 10_000, 0)
with f4: pmax = st.number_input("Max price", 0, 10_000, 0)
m1, m2 = st.columns(2)
with m1: min_views = st.number_input("Min estView/Month", 0, 10_000_000, 0)
with m2: limit_preview = st.slider("Preview limit", 10, 2000, 200, 10)

filters = {
    "regions": [x.strip() for x in regions.split(",") if x.strip()],
    "status": None if status=="any" else status,
    "price_min": int(pmin) if pmin else None,
    "price_max": int(pmax) if pmax else None,
    "min_views": int(min_views) if min_views else None,
}

# ---- Simulation panel ----
st.divider()
st.subheader("Simulation")
mode = st.segmented_control("Change mode", ["Percent", "Set absolute"], default="Percent")
if mode == "Percent":
    pct = st.slider("Change by (%)", -90, 300, 10, 1)
    action = {"percent": pct}
else:
    new_price = st.number_input("Set new price ($)", 0, 10_000, 500)
    action = {"set": int(new_price)}

# Owner simulate endpoint first
sc, sim = api("GET",
    "/owner/price/simulate?" +
    "&".join([
        f"regions={requests.utils.quote(x)}" for x in filters["regions"]
    ]) +
    (f"&status={filters['status']}" if filters["status"] else "") +
    (f"&price_min={filters['price_min']}" if filters["price_min"] is not None else "") +
    (f"&price_max={filters['price_max']}" if filters["price_max"] is not None else "") +
    (f"&min_views={filters['min_views']}" if filters["min_views"] is not None else "") +
    (f"&percent={action['percent']}" if 'percent' in action else f"&set={action['set']}")
)

if sc == 200 and isinstance(sim, dict):
    s1, s2, s3 = st.columns(3)
    s1.metric("Affected spots", sim.get("affected", 0))
    s2.metric("Current total $", f"{sim.get('current_total', 0):,.0f}")
    s3.metric("Projected total $", f"{sim.get('projected_total', 0):,.0f}")
else:
    # fallback: approximate preview using O&M spots summary
    st.caption("Using O&M summary for preview (Owner simulate not available).")
    qc, qd = api("GET", f"/o_and_m/spots/summary?limit={limit_preview}")
    if qc == 200 and isinstance(qd, list) and qd:
        df = pd.DataFrame(qd)
        # apply filters locally when columns exist
        if "address" in df.columns and filters["regions"]:
            df = df[df["address"].fillna("").str.contains("|".join(filters["regions"]), case=False)]
        if filters["status"] and "status" in df.columns:
            df = df[df["status"] == filters["status"]]
        if "price" in df.columns and filters["price_min"] is not None:
            df = df[df["price"] >= filters["price_min"]]
        if "price" in df.columns and filters["price_max"] is not None and filters["price_max"] > 0:
            df = df[df["price"] <= filters["price_max"]]
        affected = len(df)
        current_total = int(df["price"].sum()) if "price" in df.columns else 0
        if 'percent' in action:
            projected_total = int((df["price"] * (1 + action['percent']/100.0)).sum()) if "price" in df.columns else current_total
        else:
            projected_total = int(len(df) * action['set'])
        s1, s2, s3 = st.columns(3)
        s1.metric("Affected spots (approx)", affected)
        s2.metric("Current total $ (approx)", f"{current_total:,.0f}")
        s3.metric("Projected total $ (approx)", f"{projected_total:,.0f}")
        st.dataframe(df.head(50), use_container_width=True, hide_index=True)
    else:
        st.info("No preview available.")

# ---- Commit panel ----
st.divider()
st.subheader("Commit Change")
if st.button("Apply bulk change", type="primary"):
    body = {"filters": filters, **action}
    pc, pd = api("POST", "/owner/spots/bulk-price", json=body)
    if pc in (200,201):
        st.success(pd)
    else:
        st.error(f"{pc} {pd}")

st.divider()
st.subheader("Discount Caps")
dc1, dc2 = st.columns(2)
with dc1:
    gc, gd = api("GET", "/owner/config/discounts")
    if gc == 200 and isinstance(gd, dict):
        cap = st.number_input("Default discount cap (%)", 0, 90, int(gd.get("default_cap", 15)))
        overrides = st.text_area("Region overrides (JSON)", value=json.dumps(gd.get("overrides", {}), indent=2))
    else:
        cap = st.number_input("Default discount cap (%)", 0, 90, 15)
        overrides = st.text_area("Region overrides (JSON)", value="{}")
with dc2:
    if st.button("Save caps"):
        try:
            ov = json.loads(overrides)
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
            st.stop()
        pc, pd = api("PUT", "/owner/config/discounts", json={"default_cap": int(cap), "overrides": ov})
        st.success(pd) if pc == 200 else st.error(f"{pc} {pd}")