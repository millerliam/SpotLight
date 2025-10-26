import os, json, pandas as pd, requests, streamlit as st
from datetime import date
from modules.nav import SideBarLinks

st.set_page_config(page_title="O&M Admin & Imports", page_icon="🛠️", layout="wide")
SideBarLinks()
st.title("🛠️ O&M — Admin & Imports")

API = os.getenv("API_BASE_URL", "http://127.0.0.1:4000").rstrip("/")

def api(method: str, path: str, **kw):
    url = f"{API}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=30, **kw)
        data = r.json() if "application/json" in r.headers.get("content-type","") else r.text
        return r.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}

# Try multiple candidate endpoints; return first 200/201
def try_endpoints(method, candidates):
    last = (0, {"error": "no candidates"})
    for path, payload in candidates:
        code, data = api(method, path, json=payload) if method in ("POST","PUT") else api(method, path)
        if code in (200,201):
            return code, data
        last = (code, data)
    return last

tab1, tab2, tab3, tab4 = st.tabs(["Accounts & Access","Bulk Import / Update","Corrections & Flags","Configs & Retention"])

# === TAB 1 — ACCOUNTS & ACCESS ===
with tab1:
    st.subheader("Accounts & Access")

    cA, cB = st.columns([2,3])

    with cA:
        st.markdown("**Create account**")
        first = st.text_input("First name", "Liam", key="acc_first")
        last  = st.text_input("Last name", "Miller", key="acc_last")
        email = st.text_input("Email", "liam@example.com", key="acc_email")
        role  = st.selectbox("Role", ["sales","ops","admin"], index=1, key="acc_role")
        active = st.checkbox("Active", True, key="acc_active")

        if st.button("Create account", type="primary", use_container_width=True):
            payload = {"firstName": first, "lastName": last, "email": email, "role": role, "active": bool(active)}
            code, data = try_endpoints("POST", [
                ("/o_and_m/accounts", payload),
                ("/o_and_m/insert", {"entity":"account", **payload}),
            ])
            st.success(data) if code in (200,201) else st.error(f"{code} {data}")

        st.divider()
        st.markdown("**Access requests (from Sales)**")
        code, data = try_endpoints("GET", [
            ("/o_and_m/requests?type=access&status=open", None),
            ("/o_and_m/requests?status=open", None),
        ])
        if code == 200 and isinstance(data, list) and data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            sel = st.number_input("Request ID to approve/deny", min_value=1, step=1)
            action = st.selectbox("Action", ["approve","deny"])
            if st.button("Apply"):
                c2, d2 = try_endpoints("PUT", [(f"/o_and_m/requests/{int(sel)}", {"action": action})])
                st.success(d2) if c2 == 200 else st.error(f"{c2} {d2}")
        else:
            st.info("No open access requests or endpoint not available.")

    with cB:
        st.markdown("**Accounts**")
        limit = st.slider("Limit", 10, 500, 100, 10, key="acc_limit")
        code, data = try_endpoints("GET", [
            (f"/o_and_m/accounts?limit={limit}", None),
            (f"/o_and_m/users?limit={limit}", None),
        ])
        if code == 200 and isinstance(data, list) and data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption("Enable/disable or update role:")

            uid = st.number_input("Account/User ID", min_value=1, step=1, key="acc_uid")
            new_role = st.selectbox("New role", ["sales","ops","admin"], index=1, key="acc_newrole")
            is_active = st.checkbox("Active", True, key="acc_newactive")

            colx, coly = st.columns(2)
            if colx.button("Update role/active", use_container_width=True):
                c3, d3 = try_endpoints("PUT", [(f"/o_and_m/accounts/{int(uid)}", {"role": new_role, "active": bool(is_active)})])
                st.success(d3) if c3 == 200 else st.error(f"{c3} {d3}")

            if coly.button("Delete account", use_container_width=True):
                c4, d4 = try_endpoints("DELETE", [(f"/o_and_m/accounts/{int(uid)}", None)])
                st.success(d4) if c4 == 200 else st.error(f"{c4} {d4}")
        else:
            st.info("No accounts returned or endpoint not available.")

# === TAB 2 — BULK IMPORT / UPDATE ===
with tab2:
    st.subheader("Bulk Import / Update")

    entity = st.selectbox("Entity type", ["Regions","Buildings","Spots"], index=2)
    mode = st.segmented_control("Mode", ["Insert","Update"], default="Insert")
    uploaded = st.file_uploader("Upload CSV or JSON", type=["csv","json"])

    sample_tip = st.expander("Field hints (minimum required)")
    with sample_tip:
        st.markdown("""
**Regions**: `regionName`  
**Buildings**: `buildingName`, `address`, `regionID`  
**Spots**: `address`, `price`, `status` (free|inuse|planned|w.issue), `latitude`, `longitude`  
Optional (Spots): `imageURL`, `estViewPerMonth`, `monthlyRentCost`, `contactTel`, `endTimeOfCurrentOrder`
        """)

    df = None
    if uploaded:
        try:
            if uploaded.type.endswith("json"):
                data = json.load(uploaded)
                df = pd.DataFrame(data if isinstance(data, list) else [data])
            else:
                df = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Parse error: {e}")

    if df is not None and not df.empty:
        st.markdown("**Preview**")
        st.dataframe(df.head(25), use_container_width=True, hide_index=True)

        def validate_row(row, kind):
            missing = []
            if kind == "Regions":
                need = ["regionName"]
            elif kind == "Buildings":
                need = ["buildingName","address","regionID"]
            else:
                need = ["address","price","status","latitude","longitude"]
            for k in need:
                if pd.isna(row.get(k, None)): missing.append(k)
            return missing

        errs = []
        for i, row in df.iterrows():
            miss = validate_row(row, entity)
            if miss: errs.append((i, miss))
        if errs:
            st.error(f"Validation failed on {len(errs)} rows (showing first 10):")
            st.write(errs[:10])
        else:
            st.success("Validation passed ✅")
            if st.button(("Insert" if mode=="Insert" else "Update") + f" {len(df)} {entity[:-1]}"):
                payload_list = df.to_dict(orient="records")
                target = "regions" if entity=="Regions" else ("buildings" if entity=="Buildings" else "spots")

                # Try bulk first
                code, data = api("POST", f"/o_and_m/bulk_import?entity={target}&mode={mode.lower()}", json=payload_list)
                if code in (200,201):
                    st.success(f"Bulk {mode.lower()} OK: {data}")
                else:
                    # fallback: per-row insert/update
                    successes = failures = 0
                    prog = st.progress(0, text="Processing...")
                    for i, row in enumerate(payload_list, start=1):
                        if mode == "Insert":
                            per_code, per_data = api("POST", "/o_and_m/insert", json={"entity": target[:-1] if target.endswith('s') else target, **row})
                        else:
                            identifier = row.get("spotID") or row.get("buildingID") or row.get("regionID") or row.get("id")
                            if identifier is None:
                                failures += 1
                                prog.progress(i/len(payload_list), text=f"Skip row {i} (no identifier)")
                                continue
                            per_code, per_data = api("PUT", f"/o_and_m/{target}/{int(identifier)}", json=row)
                        if per_code in (200,201): successes += 1
                        else: failures += 1
                        prog.progress(i/len(payload_list), text=f"Processed {i}/{len(payload_list)}")
                    st.info(f"Done. Success: {successes}, Fail: {failures}")
    else:
        st.info("Upload a CSV/JSON to continue.")

# === TAB 3 — CORRECTIONS & FLAGS ===
with tab3:
    st.subheader("Corrections & Flags")

    code, data = try_endpoints("GET", [
        ("/o_and_m/corrections?status=open", None),
        ("/o_and_m/invalid_spot_reports?status=open", None),
        ("/o_and_m/invalid?status=open", None),
    ])
    if code == 200 and isinstance(data, list) and data:
        dfq = pd.DataFrame(data)
        st.dataframe(dfq, use_container_width=True, hide_index=True)
        st.caption("Pick a correction to act on:")
        cid = st.number_input("Correction/Report ID", min_value=1, step=1)
        action = st.selectbox("Action", ["apply_fix","needs_follow_up","resolve"], index=0)
        with st.form("corr_form"):
            new_values = st.text_area("New values (optional JSON)", placeholder='{"address":"123 New St"}')
            submitted = st.form_submit_button("Submit", type="primary")
        if submitted:
            payload = {"action": action}
            if new_values.strip():
                try:
                    payload["values"] = json.loads(new_values)
                except Exception as e:
                    st.error(f"Invalid JSON: {e}"); st.stop()
            c2, d2 = try_endpoints("PUT", [
                (f"/o_and_m/corrections/{int(cid)}", payload),
                (f"/o_and_m/invalid_spot_reports/{int(cid)}", payload),
            ])
            st.success(d2) if c2 == 200 else st.error(f"{c2} {d2}")
    else:
        st.info("No open corrections, or endpoint not available.")
        st.caption("Tip: You can also toggle a spot to 'w.issue' on the Spots Manager page.")

# === TAB 4 — CONFIGS & RETENTION ===
with tab4:
    st.subheader("System Configs & Data Retention")

    code, cfg = try_endpoints("GET", [( "/o_and_m/config", None )])
    if code != 200 or not isinstance(cfg, dict):
        cfg = {"default_discount_cap_pct":15,"alert_threshold_views":50000,"placeholder_api_key":"",
               "retention_days_logs":90,"retention_days_temp":30}
        st.info("Using local defaults (config endpoint not available).")

    c1, c2, c3 = st.columns(3)
    with c1:
        disc = st.number_input("Default discount cap (%)", 0, 90, int(cfg.get("default_discount_cap_pct", 15)))
        views = st.number_input("Alert threshold (monthly views)", 0, 10_000_000, int(cfg.get("alert_threshold_views", 50000)))
    with c2:
        key  = st.text_input("Placeholder API key", cfg.get("placeholder_api_key", ""))
        logs = st.number_input("Retention — logs (days)", 0, 3650, int(cfg.get("retention_days_logs", 90)))
    with c3:
        temp = st.number_input("Retention — temp data (days)", 0, 3650, int(cfg.get("retention_days_temp", 30)))
        today = st.date_input("Reference date", value=date.today())

    if st.button("Save config", type="primary"):
        payload = {"default_discount_cap_pct": int(disc),"alert_threshold_views": int(views),"placeholder_api_key": key,
                   "retention_days_logs": int(logs),"retention_days_temp": int(temp),"reference_date": str(today)}
        c3, d3 = try_endpoints("PUT", [
            ("/o_and_m/config", payload),
            ("/o_and_m/insert", {"entity":"config", **payload}),
        ])
        st.success(d3) if c3 == 200 else st.error(f"{c3} {d3}")

    st.divider()
    st.markdown("**Retention tools**")
    colA, colB = st.columns(2)
    with colA:
        older = st.number_input("Purge test/temporary orders older than N days", 7, 3650, 120)
        if st.button("Purge now"):
            c4, d4 = try_endpoints("POST", [(f"/o_and_m/retention/purge?older_than_days={int(older)}", None)])
            st.success(d4) if c4 in (200,201) else st.error(f"{c4} {d4}")
    with colB:
        if st.button("Archive logs (zip & rotate)"):
            c5, d5 = try_endpoints("POST", [("/o_and_m/retention/archive", None)])
            st.success(d5) if c5 in (200,201) else st.error(f"{c5} {d5}")
