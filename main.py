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
outcomes = {
    "belief_cc": "Measures climate change convictions on a scale from 0 (not at all accurate) to 100 (extremely accurate). The score averages agreement with four key statements regarding the necessity of climate action, human causes, and the urgency of the global emergency.",
    "policy_support": "Measures agreement with climate policies on a scale from 0 (not at all) to 100 (very much so). The score reflects average support across nine areas, including carbon taxes, public transport expansion, renewable energy investment, and the protection of natural ecosystems.",
    "share_social_media": "Measures willingness to share a climate-fact about meat and dairy consumption on social media. Participants were presented with an educational post and asked if they would share it.",
    "wept": "Measures real-world pro-environmental behavior using the Work for Environmental Protection Task (WEPT). Participants performed voluntary, repetitive cognitive tasks to earn tree-planting donations."
}

with sb_panel:
    st.header("⚙️ Customise Data")
    st.markdown('<div style="margin: 5px 0; border-top: 1px solid #ddd;"></div>', unsafe_allow_html=True)

    with st.container():
        st.subheader("Climate Engagement Metric")
        outcome_var_selection = st.selectbox(
            "Please select a metric to visualise on the map:",
            options = list(outcome_var_mapper.keys()),
            format_func = lambda x: outcome_var_mapper[x],
        )

        info_text = outcomes.get(outcome_var_selection)
        with st.popover(f"Info on Metric"):
            st.markdown(f"**{outcome_var_mapper[outcome_var_selection]}**")
            st.write(info_text)
    
    with st.container():
        st.subheader("Focus of Analysis")
        ctr_filter_crit = st.radio(
            "",
            options=["Average Level", "Opinion Heterogeneity (Std. Deviation)"],
            index=0, 
            #help="",
            label_visibility="collapsed"
        )

    with st.container():
        st.subheader("Country Filters")

        with st.expander("Top or Bottom scores"):
            #ctr_filter_crit = st.radio(
            #    "Select criterion for filtering:",
            #    options=["Average levels", "Polarisation"],
            #    index = None, 
            #    key="ctr_filter_crit"
            #)
            num_ctr_filter = st.slider(
                "Number of countries to display:", 
                1, 63, 63, 
                disabled=(ctr_filter_crit is None), 
                key="num_ctr_filter",
                on_change=reset_multiselect
            )
            top_bottom = st.segmented_control(
                label="Top or bottom", 
                options=["Top", "Bottom"], 
                default="Top", 
                disabled=(ctr_filter_crit is None), 
                key="top_bottom",
                on_change=reset_multiselect
            )
            
            reset_ctr_1 = st.button(
                "Reset filters", 
                on_click=reset_all_filters#reset_session_state, 
                #args=("ctr_filter_crit", "num_ctr_filter", "top_bottom"),
                )
            if reset_ctr_1:
                ctr_filter_crit = None
                num_ctr_filter = 63
                top_bottom = "Top"

            # Filter data
            plot_data = update_country_data(
                country_gdf,
                outcome_var_selection,
                ctr_filter_crit,
                num_ctr_filter,
                top_bottom,
            )
        
        with st.expander("Selected countries"):

            current_list = sorted(plot_data["name"].unique().tolist())
            #st.session_state["country_shortlist"] = sorted(country_gdf["name"].unique().tolist())

            countries_to_display = st.multiselect(
                "You can remove countries from the map:",
                options=current_list,#st.session_state["country_shortlist"],
                default=current_list, #st.session_state["country_shortlist"], 
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
            plot_data = plot_data[plot_data["name"].isin(countries_to_display)]
####################################################################################################

# Check data after filtering
if plot_data.empty:
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
folium.TileLayer('CartoDB PositronNoLabels').add_to(base)


# Geojson layers to show data as choropleths

# Color mappings
from src.utils import generate_colormaps
cm_mean, cm_std = generate_colormaps(
    outcome_var_selection, country_gdf, outcome_var_mapper, mean_mapper, disp_mapper)


#cm_mean.add_to(m)
#cm_std.add_to(m)

# Tooltips
tooltip_mean = folium.GeoJsonTooltip(
    fields=["name", mean_mapper[outcome_var_selection]],
    aliases=["Country:", "Avg. " + outcome_var_mapper[outcome_var_selection]],
    labels=True,
)
tooltip_std = folium.GeoJsonTooltip(
    fields=["name", disp_mapper[outcome_var_selection]],
    aliases=["Country:", "Opinion Heterogeneity on " + outcome_var_mapper[outcome_var_selection]],
    labels=True,
)

# Define layers as feature groups, to be passed to st_folium to avoid rerendering
fg_mean = folium.FeatureGroup(name="Average levels", control=True, overlay=False)
fg_std = folium.FeatureGroup(name="Polarisation", control=True, overlay=False)

# Layer definitions
geojson_cm_mean = folium.GeoJson(
    plot_data,
    name="Average",
    style_function=lambda feature: {
        "fillColor": cm_mean(feature["properties"][mean_mapper[outcome_var_selection]])
        if feature["properties"][mean_mapper[outcome_var_selection]] is not None
        else "lightgray",
        "color": "white",
        "fillOpacity": 0.7,
        "weight": 0.5,
    },
    overlay=False, 
    tooltip=tooltip_mean,
).add_to(fg_mean)

geojson_cm_std = folium.GeoJson(
    plot_data,
    name="Polarisation",
    style_function=lambda feature: {
        "fillColor": cm_std(feature["properties"][disp_mapper[outcome_var_selection]])
        if feature["properties"][disp_mapper[outcome_var_selection]] is not None
        else "lightgray",
        "color": "white",
        "fillOpacity": 0.7,
        "weight": 0.5,
    },
    overlay=False,
    tooltip=tooltip_std,
).add_to(fg_std)

# display map in middle panel
if ctr_filter_crit == "Average Level":
    active_fgs = [base, fg_mean]
    cm_mean.add_to(m) 
else:
    active_fgs = [base, fg_std]
    cm_std.add_to(m)
    

with map_panel:
    map_data = st_folium(
            m, 
            use_container_width = True, 
            feature_group_to_add=active_fgs,#[base, fg_mean, fg_std],
            layer_control=None,#folium.LayerControl(position="topright", collapsed=False),
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
    #rank_avg = country_gdf.loc[country_gdf["code_alpha3"] == country_code_a3, mean_mapper[outcome_var_selection] + "_rank"].values[0]
    #rank_std = country_gdf.loc[country_gdf["code_alpha3"] == country_code_a3, disp_mapper[outcome_var_selection] + "_rank"].values[0]
    best_intervention = country_gdf.loc[country_gdf["code_alpha3"] == country_code_a3, "best_intv_" + outcome_var_selection].values[0]

    # Header with flag and country name
    flag, ctr_name_subh = st.columns([0.2, 0.8], vertical_alignment="bottom")
    with flag:
        st.image(f"flags/{country_code_a2.lower()}.png", width="stretch")
    with ctr_name_subh:
        st.subheader(country_name)
    
    # Basic information
    #st.write(f"Country rank for average {outcome_var_mapper[outcome_var_selection]}: {rank_avg}")
    #st.write(f"Country rank for polarisation of {outcome_var_mapper[outcome_var_selection]}: {rank_std}")

    current_metric_col = mean_mapper[outcome_var_selection] if ctr_filter_crit == "Average Level" else disp_mapper[outcome_var_selection]
    current_value = country_gdf.loc[country_gdf["code_alpha3"] == country_code_a3, current_metric_col].values[0]

    st.write(f"**{outcome_var_mapper[outcome_var_selection]} ({'Average' if ctr_filter_crit == 'Average Level' else 'Opinion Heterogeneity'}):** {current_value:.2f}")#st.write(f"{outcome_var_mapper[outcome_var_selection]} ({ctr_filter_crit}): {current_value:.2f}")

    interventions = {
        "DynamicNorm": {
            "title": "Dynamic Social Norms",
            "description": "Informs participants of how norms are changing and “more and more people are becoming concerned about climate change”, suggesting that people should take action."
        },
        "Identity-Social-Norms-Intervention": {
            "title": "Work Together Norm",
            "description": "Combines referencing a social norm (i.e. 'a majority of people are taking steps to reduce their carbon footprint') with an invitation to 'join in' and work together with fellow citizens toward this common goal"
        },
        "CollectAction": {
            "title": "Effective Collective Action",
            "description": "Features examples of successful collective action that have had meaningful effects on climate policies (e.g. protests) or have solved past global issues (e.g. the restoration of the ozone layer)."
        },
        "PsychDistance": {
            "title": "Psychological Distance",
            "description": "Frames climate change as a proximal risk by using examples of recent natural disasters caused by climate change in each participants’ nation and prompts them to write about the climate impacts on their community."
        },
        "SystemJust": {
            "title": "System Justification",
            "description": "Frames climate change as threatening to the way of life to each participant’s nation, and makes an appeal to climate action, as the patriotic response."
        },
        "FutureSelfCont": {
            "title": "Future-Self Continuity",
            "description": "Emphasizes identification with future selves by asking each participant to project themselves into the future and write a letter addressed to themselves in the present, describing the actions they would have wanted to take regarding climate change."
        },
        "NegativeEmotions": {
            "title": "Negative Emotions",
            "description": "Exposes participants to ecologically valid scientific facts regarding the impacts of climate change framed in a ‘doom and gloom’ style of messaging that were drawn from different real-world news and media sources."
        },
        "PluralIgnorance": {
            "title": "Pluralistic Ignorance",
            "description": "Presents real public opinion data collected by the United Nations that shows what percentage of people in each participant’s country agree that climate change is a global emergency"
        },
        "Letter2Future": {
            "title": "Letter to Future Generation",
            "description": "Emphasizes how one’s current actions impact future generations by asking participants to write a letter to a socially close child who will read it in 25 years when they are an adult, describing current actions towards ensuring a habitable planet."
        },
        "BindingMoral": {
            "title": "Binding Moral Foundations",
            "description": "Invokes authority (e.g. 'From scientists to experts in the military, there is near universal agreement'), purity (e.g. keep our air, water, and land pure), and ingroup-loyalty (e.g., 'it is the American solution') moral foundations."
        },
        "ScientificConsensus": {
            "title": "Scientific Consensus",
            "description": "Informs participants that '99% of expert climate scientists agree that the Earth is warming, and climate change is happening, mainly because of human activity'."
        },
    }

    intervention_details = interventions.get(best_intervention, {})
    full_name = intervention_details.get("title", best_intervention)
    description = intervention_details.get("description", "No detailed information available for this intervention.")

    st.write(f"**Best psychological intervention to promote this metric:** {full_name}")

    with st.popover("Info on Intervention"):
        st.markdown(f"**{full_name}**")
        st.write(description)

    st.markdown('<div style="margin: 5px 0; border-top: 1px solid #ddd;"></div>', unsafe_allow_html=True)


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
        fig.update_traces(spanmode='hard')
        st.plotly_chart(fig, use_container_width=True)

    


      




    