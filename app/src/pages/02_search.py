# pages/SearchSpots.py
import streamlit as st
import requests
import pandas as pd
from modules.nav import SideBarLinks

API_URL = "http://web-api:4000/o_and_m"

st.title("Search Spots")

SideBarLinks()

def search_spots(query: str):
    try:
        r = requests.get(f"{API_URL}/search", params={"query": query}, timeout=10)
        if r.status_code == 200:
            data = r.json().get("spots", [])
            return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        st.error(f"Search error: {e}")
    return pd.DataFrame()

query = st.text_input("Search", placeholder="Enter address, street, or city...")

if query:
    results_df = search_spots(query)
    if not results_df.empty:
        for _, spot in results_df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.image(spot.get("imageURL", "https://placehold.co/100x100"), width=100)
                with c2:
                    st.write(f"**{spot['address']}**")
                    st.write(f"Price: **${spot['price']}**")
                    st.caption(f"Estimated views: {spot.get('estViewPerMonth', 'N/A')}")
    else:
        st.info("No results found.")
else:
    st.caption("Enter a search term to begin.")
