# 31_Owner_Deals_and_Knowledge.py
import os, sys, json, requests, pandas as pd, streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from modules.nav import SideBarLinks

st.set_page_config(page_title="Owner • Deals & Knowledge", page_icon="📚", layout="wide")
SideBarLinks()
st.title("📚 Deals & Knowledge Base")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def api(method: str, path: str, **kw):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=25, **kw)
        data = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

# ---- Search / list deals ----
st.subheader("Search Deals")
c1, c2, c3, c4 = st.columns([2,1,1,1])
with c1: q = st.text_input("Query (client, notes, region, etc.)", "")
with c2: region = st.text_input("Region", "")
with c3: client = st.text_input("Client", "")
with c4: limit = st.slider("Limit", 10, 500, 50, 10)

params = []
if q.strip(): params.append(f"query={requests.utils.quote(q.strip())}")
if region.strip(): params.append(f"region={requests.utils.quote(region.strip())}")
if client.strip(): params.append(f"client={requests.utils.quote(client.strip())}")
params.append(f"limit={limit}")
query_str = "&".join(params)

code, data = api("GET", f"/owner/deals?{query_str}") if query_str else api("GET", "/owner/deals?limit=50")
if code == 200 and isinstance(data, list) and data:
    df = pd.DataFrame(data)
    order_cols = [c for c in ["dealID","client","price","discount_pct","regions","term","repeat_count","notes","updated_at"] if c in df.columns]
    if order_cols:
        st.dataframe(df[order_cols], use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No deals found (or /owner/deals endpoint not available yet).")

st.divider()

# ---- Deal details: pick an ID, view details + notes timeline ----
st.subheader("Deal Details")
deal_id = st.number_input("dealID", min_value=1, step=1, value=1)
if st.button("Load deal"):
    dc, dd = api("GET", f"/owner/deals/{int(deal_id)}")
    if dc == 200 and isinstance(dd, dict):
        left, right = st.columns([2,1])
        with left:
            st.markdown("**Overview**")
            st.json(dd)
        with right:
            st.markdown("**Notes**")
            notes = dd.get("notes") if isinstance(dd.get("notes"), list) else []
            if notes:
                st.table(pd.DataFrame(notes))
            else:
                st.caption("No notes recorded.")
    else:
        st.error(f"Failed to load: {dc} {dd}")

# ---- Create / Update deal ----
st.divider()
st.subheader("Create / Update Deal")

tabC, tabU, tabN = st.tabs(["Create", "Update", "Add Note"])

with tabC:
    c1, c2, c3 = st.columns(3)
    client = c1.text_input("Client (company/person)")
    price = c2.number_input("Price ($)", 0, 10_000_000, 5000)
    discount = c3.number_input("Discount (%)", 0, 90, 0)
    regions = st.text_input("Regions (comma-sep)", "Gainesville")
    spots = st.text_input("Spot IDs (comma-sep)", "")
    term = st.text_input("Term (e.g., 3 months)", "3 months")
    repeat_count = st.number_input("Repeat count", 0, 1000, 0)
    contact = st.text_input("Contact person", "")
    notes = st.text_area("Notes / knowledge", "")
    links = st.text_area("Attachments/Links (one per line)", "")

    if st.button("Create deal", type="primary"):
        payload = {
            "client": client, "price": int(price), "discount_pct": int(discount),
            "regions": [x.strip() for x in regions.split(",") if x.strip()],
            "spotIDs": [int(x) for x in spots.split(",") if x.strip().isdigit()],
            "term": term, "repeat_count": int(repeat_count),
            "contact": contact or None, "notes": notes or "",
            "links": [x.strip() for x in links.splitlines() if x.strip()],
        }
        pc, pd = api("POST", "/owner/deals", json=payload)
        if pc in (200,201):
            st.success(pd)
        else:
            # Fallback to O&M insert if Owner endpoint not present
            fb = {"entity":"deal", **payload}
            fc, fd = api("POST", "/o_and_m/insert", json=fb)
            st.success(fd) if fc in (200,201) else st.error(f"{pc} {pd}")

with tabU:
    uid = st.number_input("dealID to update", min_value=1, step=1)
    upd = st.text_area("Update JSON", placeholder='{"price":6000,"discount_pct":10,"notes":"updated terms"}')
    if st.button("Update deal"):
        try:
            body = json.loads(upd)
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
            st.stop()
        uc, ud = api("PUT", f"/owner/deals/{int(uid)}", json=body)
        if uc == 200:
            st.success(ud)
        else:
            st.error(f"{uc} {ud}")

with tabN:
    nid = st.number_input("dealID for note", min_value=1, step=1, key="note_deal")
    note = st.text_area("Note text")
    if st.button("Add note"):
        nc, nd = api("POST", f"/owner/deals/{int(nid)}/notes", json={"note": note})
        st.success(nd) if nc in (200,201) else st.error(f"{nc} {nd}")