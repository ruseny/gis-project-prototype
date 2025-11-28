import streamlit as st
st.set_page_config(layout = "wide")
st.markdown("""
    <style>
        [data-testid="stSidebar"] { min-width: 400px; max-width: 800px; })
    </style>
""", unsafe_allow_html=True)

import folium
from streamlit_folium import st_folium
from folium.plugins import GroupedLayerControl

import json
import pandas as pd

import altair as alt
import branca

@st.cache_data
def read_geojson(path):
    with open(path, "r") as dir:
        data = json.load(dir)
    return data
country_geojson = read_geojson("countries_filtered.geo.json")

@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    return df
survey_data = load_data("mock_survey_data.csv")
country_data = load_data("mock_country_data.csv")

@st.cache_data
def get_country_aggregates(df):
    agg = df[df["intervention"] == "control"]\
        .groupby("country_code")[["belief_cc", "policy_support", "share_social_media", "wept"]]\
        .mean().reset_index()
    return agg
country_aggregates = get_country_aggregates(survey_data)

risk_factor_mapper = {
    None : "None", 
    "risk_factor_1" : "Risk Factor 1",
    "risk_factor_2": "Risk Factor 2"
}

outcome_var_mapper = {
    "belief_cc" : "Belief in Climate Change",
    "policy_support": "Policy Support",
    "share_social_media": "Sharing information on Social Media",
    "wept": "Work for Environmental Protection Task"
}

intervention_mapper = {
    "psychological_distance": "Psychological Distance",
    "letter_future_gen": "Letter to Future Generations",
    "effective_collective_action": "Effective Collective Action",
    "future_self_continuity": "Future Self Continuity",
    "system_justification": "System Justification",
    "scientific_consensus": "Scientific Consensus",
    "binding_moral_foundations": "Binding Moral Foundations",
    "dynamic_social_norms": "Dynamic Social Norms",
    "pluralistic_ignorance": "Pluralistic Ignorance",
    "negative_emotions": "Negative Emotions",
    "working_together_normative_appeal": "Working Together Normative Appeal"
}

st.title("Psychology of Climate Change - Prototype")


with st.sidebar:

    st.title("Variable selection")

    with st.container(border = True, gap = None):
        st.subheader("Country Risk Factor")
        risk_factor_selection = st.selectbox(
            "Please select a risk factor to visualise:",
            options = risk_factor_mapper, 
            format_func = lambda x: risk_factor_mapper[x]
        )
        if risk_factor_selection:
            with st.popover(f"info"):
                st.write(f"Detailed information about {risk_factor_mapper[risk_factor_selection]}.")

    with st.container(border = True, gap = None):
        st.subheader("Outcome Variable")
        outcome_var_selection = st.selectbox(
            "Please select an outcome variable to visualise:",
            options = outcome_var_mapper,
            format_func = lambda x: outcome_var_mapper[x]
        )
        with st.popover(f"info"):
            st.write(f"Detailed information about {outcome_var_mapper[outcome_var_selection]}.")

    with st.container(border = True, gap = None):
        st.subheader("Intervention")
        intervention_selection = st.selectbox(
            "Please select an intervention to visualise:",
            options = intervention_mapper,
            format_func = lambda x: intervention_mapper[x]
        )
        with st.popover(f"info"):
            st.write(f"Detailed information about {intervention_mapper[intervention_selection]}.")
    
    st.title("Demographic filters")

    with st.expander("Click to expand"):
        age_filter = st.slider("Select age range:", 18, 70, (18, 70))
        gender_filter = st.multiselect("Select gender(s):", options = ["male", "female", "nonbinary or other"])
        education_filter = st.multiselect("Select education level(s):", options = ["0 to 6 years", "7 to 12 years", "13 to 16 years", "17 or more years"])
        income_filter = st.multiselect("Select income level(s):", options = ["less than 10K", "10K to 15K", "15K to 25K", "25K to 50K", "50K to 100K", "100K to 150K", "150K to 200K", "more than 200K"])
        perc_ses_filter = st.multiselect("Select perceived socioeconomic status level(s):", options = ["0-10%", "10-20%", "20-30%", "30-40%", "40-50%", "50-60%", "60-70%", "70-80%", "80-90%", "90-100%"])
        sp_ideology_filter = st.slider("Select range for sociopolitical ideology:", 0, 100, (0, 100))
        econ_ideology_filter = st.slider("Select range for economic ideology:", 0, 100, (0, 100))

    
view_choice = st.segmented_control(
    label = "Select view mode",
    options = ["Global view", "Country comparison"],
    default = "Global view"
)

if risk_factor_selection:
    st.write("""
             You can display country colours based on either the risk factor or the average outcome variable. 
             You can select this from the layer control at the top-right of the map.
             """)
st.write("To display the visualisation for a country, please click on the chart icon.")

if view_choice == "Global view":

    m = folium.Map(zoom_start = 2.45, location = [47.689521, 9.188241])

    outcome_choropleth = folium.Choropleth(
        geo_data = country_geojson, 
        data = country_aggregates,
        columns = ["country_code", outcome_var_selection],
        key_on = "feature.id", 
        fill_color = "YlGn", 
        bins = 8,
        highlight = True, 
        name = outcome_var_mapper[outcome_var_selection], 
        legend_name = f"Scale for {outcome_var_mapper[outcome_var_selection]}"
    ).add_to(m)

    if risk_factor_selection:
        risk_factor_choropleth = folium.Choropleth(
            geo_data = country_geojson, 
            data = country_data,
            columns = ["country_code", risk_factor_selection],
            key_on = "feature.id", 
            fill_color = "OrRd", 
            bins = 8,
            highlight = True,
            name = risk_factor_mapper[risk_factor_selection],
            legend_name = f"Scale for {risk_factor_mapper[risk_factor_selection]}"
        ).add_to(m)

        GroupedLayerControl(
            groups = {
                "Country colours (control)": [outcome_choropleth, risk_factor_choropleth]
            }
        ).add_to(m)

    # create an icon for chart popups
    chart_icon = folium.CustomIcon(
        icon_image = "candlestick-chart.png", 
        icon_size = (20, 20), 
        icon_anchor = (10, 20), 
        popup_anchor = (0, -10)
    )

    # get chart data for usa
    chart_data_usa = survey_data.loc[
        (survey_data["country_code"] == "USA") &
        (survey_data["intervention"].isin(["control", intervention_selection])), 
        ["intervention", outcome_var_selection]
    ]
    # create chart object
    chart_object_usa = alt.Chart(chart_data_usa).mark_boxplot().encode(
        alt.X("intervention:N"), 
        alt.Y(outcome_var_selection + ":Q").scale(zero = False),
        alt.Color("intervention:N").legend(None)
    )
    # pass the object to vega
    chart_vega_usa = folium.VegaLite(
        chart_object_usa,
        width = 300,
        height = 200
    )
    
    # pass the vega to popup
    popup_usa = folium.Popup("Here will be the chart", max_width = 300)
    #chart_vega_usa.add_to(popup_usa)

    # define the marker
    marker_usa = folium.Marker(
        location = [38.0,-97.0], 
        icon = chart_icon, 
        lazy = True
    )

    # pass the popup to the marker
    popup_usa.add_to(marker_usa)
    marker_usa.add_to(m)

    map = st_folium(
        m, 
        use_container_width = True
    )

    

if view_choice == "Country comparison":
    
    m1 = folium.Map(zoom_start = 2.45, location = [47.689521, 9.188241])
    m2 = folium.Map(zoom_start = 2.45, location = [47.689521, 9.188241])

    col1, col2 = st.columns(2)
    with col1:
        map1 = st_folium(m1, use_container_width = True, key = "comp_map_1")
    with col2:
        map2 = st_folium(m2, use_container_width = True, key = "comp_map_2")
