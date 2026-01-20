"""
Streamlit frontend application for geographically
visualising the psychology of climate change data.
"""

### Module imports #####################
# Main module
import streamlit as st

# Map modules
import folium
from streamlit_folium import st_folium

# Import custom functions and variables
from src.utils import *
from src.constants import *
from src.session_state import *
init_session_state()

import plotly.express as px  # for plotting
#######################################

### Page Layout #########################################################
st.set_page_config(layout = "wide")

st.title("Psychology of Climate Change")

sb_panel = st.sidebar
map_panel, info_panel = st.columns([0.67, 0.33])
#######################################################################

### Load and process data ############################################################
survey_data = load_data("data/data_individual_clean2.csv")
country_aggregates = load_data("data/data_country_final.csv")
country_basics = load_data("data/country_data_basic.csv")
country_gdf_raw = read_gpd("data/countries.geo.json")
country_gdf = merge_country_data(country_gdf_raw, country_aggregates, country_basics)
#######################################################################################

### Sidebar for data customisation ################################################################
with sb_panel:
    st.header("Customise Data")

    with st.container():
        st.subheader("Measurement")
        outcome_var_selection = st.selectbox(
            "Please select a measurement to visualise on the map:",
            options = list(outcome_var_mapper.keys()),
            format_func = lambda x: outcome_var_mapper[x]
        )
        with st.popover(f"info"):
            st.write(f"Detailed information about {outcome_var_mapper[outcome_var_selection]}.")
    
    with st.container():
        st.subheader("Country Filters")

        with st.expander("Top or Bottom scores"):
            ctr_filter_crit = st.radio(
                "Select criterion for filtering:",
                options=["Average levels", "Polarisation"],
                index = None, 
                key="ctr_filter_crit"
            )
            num_ctr_filter = st.slider(
                "Number of countries to display:", 
                1, 61, 61, 
                disabled=(ctr_filter_crit is None), 
                key="num_ctr_filter"
            )
            top_bottom = st.segmented_control(
                label="Top or bottom", 
                options=["Top", "Bottom"], 
                default="Top", 
                disabled=(ctr_filter_crit is None), 
                key="top_bottom"
            )
            reset_ctr_1 = st.button(
                "Reset filters", 
                on_click=reset_session_state, 
                args=("ctr_filter_crit", "num_ctr_filter", "top_bottom"),
                )
            if reset_ctr_1:
                ctr_filter_crit = None
                num_ctr_filter = 61
                top_bottom = "Top"
            # Update data
            country_gdf = update_country_data(
                country_gdf,
                outcome_var_selection,
                ctr_filter_crit,
                num_ctr_filter,
                top_bottom,
            )
        
        with st.expander("Selected countries"):
            st.session_state["country_shortlist"] = sorted(country_gdf["name"].unique().tolist())
            countries_to_display = st.multiselect(
                "You can remove countries from the map:",
                options=st.session_state["country_shortlist"],
                default=st.session_state["country_shortlist"], 
                key="countries_to_display"
            )
            reset_ctr_2 = st.button(
                "Reset country selection", 
                on_click=reset_session_state, 
                args=("countries_to_display",),
            )
            if reset_ctr_2:
                countries_to_display = st.session_state["country_shortlist"]
            # Update data
            country_gdf = country_gdf[country_gdf["name"].isin(countries_to_display)]
####################################################################################################

# Check data after filtering
if country_gdf.empty:
    st.warning("No data available for the selected filters. Please adjust your selections in the sidebar.")
    st.stop()


### Map ##############################################################################################
# Empty map
m = folium.Map(
    zoom_start = 2, 
    location = [47.689521, 9.188241], 
    tiles=None, 
    zoom_control="bottomleft")

# Base layer that won't appear in layer control, but can be overlaid by geojson layers
base = folium.FeatureGroup(name="Base Map", overlay=True, control=False)
folium.TileLayer('OpenStreetMap').add_to(base)

# Geojson layers to show data as choropleths

# Color mappings
from src.utils import generate_colormaps
cm_mean, cm_std = generate_colormaps(
    outcome_var_selection, country_gdf, outcome_var_mapper, mean_mapper, disp_mapper)
cm_mean.add_to(m)
cm_std.add_to(m)

# Tooltips
tooltip_mean = folium.GeoJsonTooltip(
    fields=["name", mean_mapper[outcome_var_selection]],
    aliases=["Country:", "Avg. " + outcome_var_mapper[outcome_var_selection]],
    labels=True,
)
tooltip_std = folium.GeoJsonTooltip(
    fields=["name", disp_mapper[outcome_var_selection]],
    aliases=["Country:", "Polarisation in " + outcome_var_mapper[outcome_var_selection]],
    labels=True,
)

# Define layers as feature groups, to be passed to st_folium to avoid rerendering
fg_mean = folium.FeatureGroup(name="Average levels", control=True, overlay=False)
fg_std = folium.FeatureGroup(name="Polarisation", control=True, overlay=False)

# Layer definitions
geojson_cm_mean = folium.GeoJson(
    country_gdf,
    name="Average",
    style_function=lambda feature: {
        "fillColor": cm_mean(feature["properties"][mean_mapper[outcome_var_selection]])
        if feature["properties"][mean_mapper[outcome_var_selection]] is not None
        else "lightgray",
        "color": "black",
        "fillOpacity": 0.7,
        "weight": 0.5,
    },
    overlay=False, 
    tooltip=tooltip_mean,
).add_to(fg_mean)
geojson_cm_std = folium.GeoJson(
    country_gdf,
    name="Polarisation",
    style_function=lambda feature: {
        "fillColor": cm_std(feature["properties"][disp_mapper[outcome_var_selection]])
        if feature["properties"][disp_mapper[outcome_var_selection]] is not None
        else "lightgray",
        "color": "black",
        "fillOpacity": 0.7,
        "weight": 0.5,
    },
    overlay=False,
    tooltip=tooltip_std,
).add_to(fg_std)

# display map in middle panel
with map_panel:
    map_data = st_folium(
            m, 
            use_container_width = True, 
            feature_group_to_add=[base, fg_mean, fg_std],
            layer_control=folium.LayerControl(position="topright", collapsed=False),
    )
    # st.write(map_data) # for debugging

# Capture last clicked country
if map_data["last_active_drawing"]:
    clicked_country = {
        "name": map_data["last_active_drawing"]["properties"]["name"], 
        "code_alpha3": map_data["last_active_drawing"]["properties"]["code_alpha3"], 
        "code_alpha2": map_data["last_active_drawing"]["properties"]["code_alpha2"]
    }
    st.session_state["last_clicked_country"] = clicked_country

# st.write(st.session_state["last_clicked_country"]) # for debugging
###################################################################################################

### Info Panel ######################################################################################
with info_panel:
    # Stop script if no country selected
    if st.session_state["last_clicked_country"] is None:
        st.write("Click on a country on the map to see more information here.")
        st.stop()
    # Stop script if selected country is filtered out
    if st.session_state["last_clicked_country"]["name"] not in country_gdf["name"].values:
        st.write("The selected country is currently filtered out. Please adjust your filters in the sidebar.")
        st.stop()

    # Continue if country selected
    country_code_a3 = st.session_state["last_clicked_country"]["code_alpha3"]
    country_code_a2 = st.session_state["last_clicked_country"]["code_alpha2"]
    country_name = st.session_state["last_clicked_country"]["name"]
    rank_avg = country_gdf.loc[country_gdf["code_alpha3"] == country_code_a3, mean_mapper[outcome_var_selection] + "_rank"].values[0]
    rank_std = country_gdf.loc[country_gdf["code_alpha3"] == country_code_a3, disp_mapper[outcome_var_selection] + "_rank"].values[0]
    best_intervention = country_gdf.loc[country_gdf["code_alpha3"] == country_code_a3, "best_intv_" + outcome_var_selection].values[0]

    # Header with flag and country name
    flag, ctr_name_subh = st.columns([0.2, 0.8], vertical_alignment="bottom")
    with flag:
        st.image(f"flags/{country_code_a2.lower()}.png", width="stretch")
    with ctr_name_subh:
        st.subheader(country_name)
    
    # Basic information
    st.write(f"Country rank for average {outcome_var_mapper[outcome_var_selection]}: {rank_avg}")
    st.write(f"Country rank for polarisation of {outcome_var_mapper[outcome_var_selection]}: {rank_std}")
    st.write(f"Best intervention for {outcome_var_mapper[outcome_var_selection]}: {best_intervention}")
    with st.popover("Info on intervention"):
        st.write("Detailed information about the best intervention.")

    st.write("---")

    # Chart of outcome variable

    # Grouped or not, shown side by side
    gr_col1, gr_col2 = st.columns(2)
    with gr_col1:
        grouped_viz = st.toggle(
            label="Compare groups?",
            value=False,
        )
    with gr_col2:
        if grouped_viz:
            group_selection = st.selectbox(
                "Select groups to compare:",
                options = list(other_var_mapper.keys()),
                format_func = lambda x: other_var_mapper[x]
            )
        else:
            group_selection = None
    
    # Plot outcome variable distribution
    if group_selection is None:
        plot_data = survey_data.loc[survey_data["alpha3"] == country_code_a3, outcome_var_selection]
        fig = px.histogram(
            plot_data,
            x=outcome_var_selection,
            nbins=30,
            title=f"Distribution of {outcome_var_mapper[outcome_var_selection]} in {country_name}",
            labels={outcome_var_selection: outcome_var_mapper[outcome_var_selection]},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        plot_data = survey_data.loc[survey_data["alpha3"] == country_code_a3, [outcome_var_selection, group_selection]]
        plot_data["group_bins"] = pd.cut(plot_data[group_selection], bins=3, labels= ["Young", "Middle-aged", "Old"])
        fig = px.violin(
            plot_data,
            x="group_bins",
            y=outcome_var_selection,
            title=f"Distribution of {outcome_var_mapper[outcome_var_selection]} in {country_name}, grouped by {other_var_mapper[group_selection]}",
            labels={
                outcome_var_selection: outcome_var_mapper[outcome_var_selection],
                group_selection: other_var_mapper[group_selection], 
                "group_bins": "Age Group"
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    


      




    