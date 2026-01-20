import streamlit as st

def init_session_state():
    if "last_clicked_country" not in st.session_state:
        st.session_state["last_clicked_country"] = None
    if "full_country_list" not in st.session_state:
        st.session_state["full_country_list"] = [
            "Algeria","Armenia","Australia","Austria","Belgium",
            "Brazil","Bulgaria","Canada","Chile","China",
            "Czech Republic","Denmark","Ecuador","Finland",
            "France","Gambia","Germany","Ghana","Greece","India",
            "Ireland","Israel","Italy","Japan","Kenya","Latvia",
            "Macedonia","Mexico","Morocco","Netherlands",
            "New Zealand","Nigeria","Norway","Peru","Philippines",
            "Poland","Portugal","Republic of Serbia","Romania",
            "Russia","Saudi Arabia","Singapore","Slovakia",
            "Slovenia","Spain","Sri Lanka","Sudan","Sweden",
            "Switzerland","Taiwan","Thailand","Turkey","Uganda",
            "Ukraine","United Arab Emirates","United Kingdom",
            "United Republic of Tanzania","United States of America",
            "Uruguay","Venezuela","Vietnam", "South Africa", "South Korea"
        ]
    if "country_shortlist" not in st.session_state:
        st.session_state["country_shortlist"] = st.session_state["full_country_list"].copy()

def reset_session_state(*keys):
    for key in keys:
        if key == "last_clicked_country":
            st.session_state[key] = None
        if key == "ctr_filter_crit":
            st.session_state[key] = None
        if key == "num_ctr_filter":
            st.session_state[key] = 61
        if key == "top_bottom":
            st.session_state[key] = "Top"
        if key == "countries_to_display":
            st.session_state[key] = st.session_state["country_shortlist"]