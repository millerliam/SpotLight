# Idea borrowed from https://github.com/fsmosca/sample-streamlit-authenticator

# This file has function to add certain functionality to the left side bar of the app

import streamlit as st

#### ------------------------ General ------------------------
def HomeNav():
    st.sidebar.page_link("Home.py", label="Home", icon="🏠")

def CustomerPageNav():
    st.sidebar.page_link("pages/01_Customer_Profile.py", label="Profile", icon="👤")
    st.sidebar.page_link("pages/03_Customer_Map.py",                 label="Map", icon="🗺️")
    st.sidebar.page_link("pages/10_Customer_Browse_and_Cart.py",     label="Browse & Cart", icon="🛒")
    st.sidebar.page_link("pages/11_Customer_Orders_and_Cancel.py",   label="Orders & Cancel", icon="🧾")

def SalesmanPageNav():
    st.sidebar.page_link("pages/40_Sales_Leads.py", label="Leads", icon="📇")
    st.sidebar.page_link("pages/41_Sales_Repeat_Clients.py", label="Repeat Clients", icon="🔁")
    st.sidebar.page_link("pages/42_Sales_Spots.py", label="Spots", icon="📍")

def AdminPageNav():
    st.sidebar.page_link("pages/20_dashboard.py", label="O&M Dashboard", icon="🖥️")
    st.sidebar.page_link("pages/21_statistics.py", label="Statistics", icon="📊")
    st.sidebar.page_link("pages/22_management_map.py", label="Management Map", icon="🗺️")
    st.sidebar.page_link("pages/23_OM_Admin_and_Imports.py", label="Admin & Imports", icon="🛠️")  


def OwnerPageNav():
    st.sidebar.subheader("Owner")
    st.sidebar.page_link("pages/30_Owner_Home.py", label="Owner Dashboard", icon="📈")
    st.sidebar.page_link("pages/31_Owner_Deals_and_Knowledge.py", label="Deals & Knowledge", icon="📚")
    st.sidebar.page_link("pages/32_Owner_Pricing_and_Discounts.py", label="Pricing & Discounts", icon="💸")
    st.sidebar.page_link("pages/33_Owner_Reviews_VIP_and_Hygiene.py", label="Reviews, VIP & Hygiene", icon="⭐")


# --------------------------------Links Function -----------------------------------------------
def SideBarLinks(show_home=False):

    # add a logo to the sidebar always
    st.sidebar.image("assets/logo.png", width=150)

    # If there is no logged in user, redirect to the Home (Landing) page
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.switch_page("Home.py")

    if show_home:
        # Show the Home page link (the landing page)
        HomeNav()

    # Show the other page navigators depending on the users' role.
    if st.session_state["authenticated"]:

        # Show World Bank Link and Map Demo Link if the user is a political strategy advisor role.
        if st.session_state["role"] == "customer":
            CustomerPageNav()

        # If the user role is usaid worker, show the Api Testing page
        if st.session_state["role"] == "salesman":
            SalesmanPageNav()

        # If the user is an administrator, give them access to the administrator pages
        if st.session_state["role"] == "o&m":
            AdminPageNav()
            
        if st.session_state["role"] == "owner":
            OwnerPageNav()
        

    if st.session_state["authenticated"]:
        # Always show a logout button if there is a logged in user
        if st.sidebar.button("Logout"):
            del st.session_state["role"]
            del st.session_state["authenticated"]
            st.switch_page("Home.py")