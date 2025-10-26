# 33_Owner_Reviews_VIP_and_Hygiene.py
import os, sys, json, requests, pandas as pd, streamlit as st
from datetime import date

# --- nav import like Customer ---
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from modules.nav import SideBarLinks

st.set_page_config(page_title="Owner • Reviews, VIP & Hygiene", page_icon="⭐", layout="wide")
SideBarLinks()
st.title("⭐ Reviews, VIP & Hygiene")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def api(method: str, path: str, **kw):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=25, **kw)
        data = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

tab1, tab2, tab3 = st.tabs(["Client Reviews", "VIP Scoring & Tagging", "Data Hygiene"])

# ---- Reviews ----
with tab1:
    st.subheader("Submit a Review")
    c1, c2, c3 = st.columns(3)
    cID = c1.number_input("Customer ID", 1, 999999, 1)
    rating = c2.slider("Rating", 1, 5, 5)
    rdate = c3.date_input("Date", value=date.today())
    text = st.text_area("Review text")
    if st.button("Submit review", type="primary"):
        payload = {"cID": int(cID), "rating": int(rating), "date": str(rdate), "text": text}
        pc, pd = api("POST", "/owner/reviews", json=payload)
        if pc in (200,201):
            st.success(pd)
        else:
            # fallback to O&M style insert
            fc, fd = api("POST", "/o_and_m/insert", json={"entity":"review", **payload})
            st.success(fd) if fc in (200,201) else st.error(f"{pc} {pd}")

    st.divider()
    st.subheader("Reviews table")
    qc, qd = api("GET", "/owner/reviews?limit=200")
    if qc == 200 and isinstance(qd, list) and qd:
        df = pd.DataFrame(qd)
        show = [c for c in ["reviewID","cID","rating","date","text","featured"] if c in df.columns]
        st.dataframe(df[show], use_container_width=True, hide_index=True)
        rid = st.number_input("reviewID to toggle featured", 1, 999999, 1)
        if st.button("Toggle featured"):
            tc, td = api("PUT", f"/owner/reviews/{int(rid)}", json={"toggle":"featured"})
            st.success(td) if tc == 200 else st.error(f"{tc} {td}")
    else:
        st.info("No reviews yet or endpoint unavailable.")

# ---- VIP ----
with tab2:
    st.subheader("Scores (90d)")
    sc, sd = api("GET", "/owner/customers/scores?period=90d")
    if sc == 200 and isinstance(sd, list) and sd:
        df = pd.DataFrame(sd)
    else:
        # fallback: compute from orders summary
        oc, od = api("GET", "/o_and_m/orders/summary?period=90d&limit=10000")
        if oc == 200 and isinstance(od, list) and od:
            dfO = pd.DataFrame(od)
            if {"cID","total"}.issubset(dfO.columns):
                spend = dfO.groupby("cID")["total"].sum().rename("spend_90d")
                freq = dfO.groupby("cID")["total"].size().rename("orders_90d")
                df = pd.concat([spend, freq], axis=1).reset_index()
                # simple score: 70% spend rank + 30% freq rank (0..100)
                df["rank_spend"] = 100 * (df["spend_90d"].rank(pct=True))
                df["rank_freq"]  = 100 * (df["orders_90d"].rank(pct=True))
                df["score"] = (0.7*df["rank_spend"] + 0.3*df["rank_freq"]).round(1)
                df["category"] = pd.cut(df["score"], bins=[-1,40,70,90,100], labels=["Low","Med","High","VIP"])
            else:
                df = pd.DataFrame()
        else:
            df = pd.DataFrame()

    if not df.empty:
        st.dataframe(df.sort_values("score", ascending=False).head(50), use_container_width=True, hide_index=True)
        thresh = st.slider("Promote to VIP if score ≥", 50, 100, 90)
        promote_ids = df.loc[df["score"] >= thresh, "cID"].astype(int).tolist()
        st.caption(f"{len(promote_ids)} candidate(s) at/above threshold.")
        if st.button("Promote selected to VIP", type="primary") and promote_ids:
            ok, fail = 0, 0
            for cid in promote_ids:
                pc, pd = api("PUT", f"/owner/customers/{cid}/vip", json={"VIP": True})
                if pc == 404:  # fallback: use customer update endpoint
                    # pull current customer, then post with VIP=true plus required fields
                    gc, gd = api("GET", f"/customer/{cid}")
                    if gc == 200 and isinstance(gd, dict):
                        body = gd.copy(); body["VIP"] = True
                        uc, ud = api("POST", f"/customer/{cid}", json=body)
                        ok += 1 if uc == 200 else 0; fail += 1 if uc != 200 else 0
                    else:
                        fail += 1
                else:
                    ok += 1 if pc in (200,201) else 0
                    fail += 1 if pc not in (200,201) else 0
            st.success(f"VIP updated. Success: {ok}, Fail: {fail}")
    else:
        st.info("No score data available.")

# ---- Hygiene ----
with tab3:
    st.subheader("Archive Creatives")
    older = st.number_input("Archive creatives older than N days", 30, 3650, 180)
    if st.button("Archive now"):
        ac, ad = api("POST", f"/owner/creatives/archive?older_than={older}")
        st.success(ad) if ac in (200,201) else st.error(f"{ac} {ad}")

    st.divider()
    st.subheader("Expired / Invalid Addresses")
    ec, ed = api("GET", "/owner/addresses/expired?limit=200")
    if ec == 200 and isinstance(ed, list) and ed:
        dfA = pd.DataFrame(ed)
        st.dataframe(dfA, use_container_width=True, hide_index=True)
        aid = st.number_input("Address/Record ID", 1, 999999, 1)
        action = st.selectbox("Action", ["fix","needs_follow_up","archive"], index=0)
        val = st.text_input("New address (if fix)")
        if st.button("Apply"):
            body = {"action": action, "value": val or None}
            pc, pd = api("PUT", f"/owner/addresses/{int(aid)}", json=body)
            st.success(pd) if pc == 200 else st.error(f"{pc} {pd}")
    else:
        st.info("No expired/invalid addresses (or endpoint unavailable).")

    st.divider()
    st.subheader("Retention")
    col1, col2 = st.columns(2)
    with col1:
        days = st.number_input("Purge temporary/test data older than (days)", 7, 3650, 120)
        if st.button("Purge"):
            pc, pd = api("POST", f"/owner/retention/purge?older_than_days={int(days)}")
            st.success(pd) if pc in (200,201) else st.error(f"{pc} {pd}")
    with col2:
        if st.button("Archive logs"):
            pc, pd = api("POST", "/owner/retention/archive")
            st.success(pd) if pc in (200,201) else st.error(f"{pc} {pd}")