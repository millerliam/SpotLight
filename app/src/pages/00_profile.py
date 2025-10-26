import streamlit as st
import requests
from modules.nav import SideBarLinks

API_URL = "http://web-api:4000/customer"
# Hardcoded for demo purposes
USERNAME = "Eric.C"
C_ID = 1

st.title("Your Profile")

SideBarLinks()

@st.cache_data(ttl=30)
def load_profile():
    r = requests.get(f"{API_URL}/{C_ID}", timeout=10)
    if r.status_code == 200:
        data = r.json()
        return {
            "username": USERNAME,
            "company": data["companyName"],
            "phone": data["TEL"],
            "email": data["email"],
            "industry": "N/A",
            "position": data["position"],
            "avatar_url": data["avatarURL"],
            "balance": data["balance"]
        }
    return None

if "profile" not in st.session_state:
    st.session_state.profile = load_profile() or {
        "username": USERNAME,
        "company": "",
        "phone": "",
        "email": "",
        "industry": "",
        "position": "",
        "avatar_url": "",
        "balance": 0
    }

left, right = st.columns([1, 2])

def row(label, key):
    data, modify = st.columns([3, 1])
    with data:
        with st.container(gap=None):
            st.write(f"**{st.session_state.profile[key]}**")
            st.caption(label)
    with modify:
        if st.button("✏️", key=f"edit_{key}", type="secondary", use_container_width=True):
            new_val = st.text_input(f"Update {label}", value=st.session_state.profile[key], key=f"input_{key}")
            if st.button("Save", key=f"save_{key}"):
                st.session_state.profile[key] = new_val
                payload = {
                    "fName": "Eric",
                    "lName": "C",
                    "email": st.session_state.profile["email"],
                    "position": st.session_state.profile["position"],
                    "companyName": st.session_state.profile["company"],
                    "totalOrderTimes": 0,
                    "VIP": 0,
                    "avatarURL": st.session_state.profile["avatar_url"],
                    "balance": st.session_state.profile["balance"],
                    "TEL": st.session_state.profile["phone"],
                }
                requests.post(f"{API_URL}/{C_ID}", json=payload, timeout=10)
                st.toast(f"{label} updated")

with left:
    with st.container(border=True, gap=None):
        ac, bc, cc = st.columns([1, 2, 1])
        with bc:
            st.image(st.session_state.profile["avatar_url"], width=120)
        st.divider()
        st.caption("Username")
        st.write(f"**{st.session_state.profile['username']}**")
        st.divider()
        row("Company", "company")
        row("Tel Number", "phone")
        row("Email", "email")
        st.divider()
        row("Industry", "industry")
        row("Position", "position")

with right:
    with st.expander("My Orders", expanded=True):
        st.info("You don't have any order yet!")
        st.button("Browse products", type="primary")

    with st.expander("Privacy Setting", expanded=False):
        st.checkbox("Show my email to teammates", value=True)
        st.checkbox("Enable two-factor authentication", value=False)
        st.checkbox("Allow analytics & diagnostics", value=True)
        st.button("Save privacy settings", type="primary")

    with st.expander("My Balance", expanded=False):
        bal_l, bal_r = st.columns([2, 1])
        with bal_l:
            st.metric("Current Balance", f"${st.session_state.profile['balance']:.2f}")
        with bal_r:
            st.button("Add Funds", type="primary", use_container_width=True)

    with st.expander("Manage Payment Method", expanded=False):
        st.write("No saved cards.")
        add_c1, add_c2 = st.columns(2)
        with add_c1:
            st.text_input("Cardholder name", placeholder="Name on card")
        with add_c2:
            st.text_input("Card number", placeholder="xxxx xxxx xxxx xxxx")
        c3, c4, c5 = st.columns([1, 1, 1])
        with c3:
            st.text_input("MM/YY", placeholder="MM/YY")
        with c4:
            st.text_input("CVC", placeholder="CVC")
        with c5:
            st.button("Add Card", type="primary", use_container_width=True)

    with st.expander("Feedback", expanded=False):
        if "feedback" not in st.session_state:
            st.session_state.feedback = ""

        st.text_area(
            "Leave your feedback",
            placeholder="Tell us what we can improve…",
            key="feedback"
        )

        cols = st.columns([1, 1])
        if cols[1].button("Clear", use_container_width=True):
            st.toast("Feedback cleared")

        if cols[0].button("Submit Feedback", type="primary", use_container_width=True):
            st.toast("Thanks for the feedback!")
