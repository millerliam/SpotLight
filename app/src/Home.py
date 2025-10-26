##################################################
# This is the main/entry-point file for the
# sample application for your project
##################################################

# Set up basic logging infrastructure
import logging
logging.basicConfig(format='%(filename)s:%(lineno)s:%(levelname)s -- %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# import the main streamlit library as well
# as SideBarLinks function from src/modules folder
import streamlit as st
from modules.nav import SideBarLinks

# streamlit supports reguarl and wide layout (how the controls
# are organized/displayed on the screen).
st.set_page_config(layout = 'wide')

# If a user is at this page, we assume they are not
# authenticated.  So we change the 'authenticated' value
# in the streamlit session_state to false.
st.session_state['authenticated'] = False

# Use the SideBarLinks function from src/modules/nav.py to control
# the links displayed on the left-side panel.
# IMPORTANT: ensure src/.streamlit/config.toml sets
# showSidebarNavigation = false in the [client] section
SideBarLinks(show_home=True)

# ***************************************************
#    The major content of this page
# ***************************************************

# set the title of the page and provide a simple prompt.
logger.info("Loading the Home page of the app")
st.title('SpotLight')
st.write('\n\n')
# st.write('### Overview:')
# st.write('\n')
st.write('#### HI! As which user would you like to log in?')

# For each of the user personas for which we are implementing
# functionality, we put a button on the screen that the user
# can click to MIMIC logging in as that mock user.

if st.button('Act as a Customer',
            type = 'primary',
            use_container_width=True):
    st.session_state['authenticated'] = True
    st.session_state['role'] = 'customer'
    st.switch_page("pages/01_Customer_Profile.py")

if st.button('Act as a Salesman',
             type = 'primary',
             use_container_width=True):
    st.session_state['authenticated'] = True
    st.session_state['role'] = 'salesman'
    st.switch_page('pages/40_Sales_Leads.py')

if st.button('Act as an Owner',
             type='primary',
             use_container_width=True):
    st.session_state['authenticated'] = True
    st.session_state['role'] = 'owner'
    st.switch_page('pages/30_Owner_Home.py')  


if st.button('Act as an O&M Admin',
            type = 'primary',
            use_container_width=True):
    st.session_state['authenticated'] = True
    st.session_state['role'] = 'o&m'
    st.session_state['first_name'] = 'SysAdmin'
    st.switch_page('pages/20_dashboard.py')
