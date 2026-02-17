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
import pandas as pd
import numpy as np 

# Import custom functions and variables
from src.utils import *
from src.constants import *
from src.session_state import *
from scipy.stats import gaussian_kde
import plotly.graph_objects as go
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
survey_data2 = load_data("data/data_individual_clean.csv")
country_aggregates = load_data("data/data_country_clean_sam2.csv")#("data/data_country_final.csv")
for metric in ["belief_cc_mean", "policy_support_mean", "share_social_media_mean"]:
    country_aggregates[metric] = country_aggregates[metric].round().astype(int)
country_basics = load_data("data/country_data_basic.csv")
country_gdf_raw = read_gpd("data/countries.geo.json")

country_gdf = merge_country_data(country_gdf_raw, country_aggregates, country_basics)
survey_data = survey_data.rename(columns={"share_social_media": "share_sm"})
country_gdf = country_gdf.rename(columns={"best_intv_share_social_media": "best_intv_share_sm"})

#######################################################################################

### Sidebar for data customisation ################################################################
outcomes = {
    "belief_cc": "Measures climate change convictions on a scale from 0 (not at all accurate) to 100 (extremely accurate). The score averages agreement with four key statements regarding the necessity of climate action, human causes, and the urgency of the global emergency.",
    "policy_support": "Measures agreement with climate policies on a scale from 0 (not at all) to 100 (very much so). The score reflects average support across nine areas, including carbon taxes, public transport expansion, renewable energy investment, and the protection of natural ecosystems.",
    "share_sm": "Measures willingness to share a climate-fact about meat and dairy consumption on social media. Participants were presented with an educational post and asked if they would share it. The values presented for this metric are percentages.",    
    "wept": "Measures real-world pro-environmental behavior using the psychological test WEPT (Work for Environmental Protection Task). Participants performed voluntary, repetitive cognitive tasks that would resuslt on tree-planting donations."
}

with sb_panel:
    st.header("⚙️ Customise Data")
    st.markdown('<div style="margin: 5px 0; border-top: 0px solid #ddd;"></div>', unsafe_allow_html=True)

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
        #disp_label = "Opinion Heterogeneity (Entropy)" if outcome_var_selection == "share_sm" else "Polarization (Std. Deviation)"
    
        ctr_filter_crit = st.radio(
            "",
            options=["Average Level", "Opinion Heterogeneity"],
            index=0, 
            label_visibility="collapsed"
        )

    with st.container():
        st.subheader("Country Filters")

        with st.expander("Top or Bottom scores"):
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
    # aliases=["Country:", "Avg. " + outcome_var_mapper[outcome_var_selection]],
    aliases=["Country:", "Average:"],

    labels=True,
)
tooltip_std = folium.GeoJsonTooltip(
    fields=["name", disp_mapper[outcome_var_selection]],
    aliases=["Country:", "Opinion Heterogeneity "],
    labels=True,
)

# Define layers as feature groups, to be passed to st_folium to avoid rerendering
fg_mean = folium.FeatureGroup(name="Average levels", control=True, overlay=False)
fg_std = folium.FeatureGroup(name="Polarisation", control=True, overlay=False)

# --- countries currently selected for display (plot_data is the filtered subset) ---
selected_a3 = set(plot_data["code_alpha3"].dropna().unique())

# FeatureGroup for countries NOT selected (black)
fg_unselected = folium.FeatureGroup(
    name="Unselected countries",
    control=False,   # hide from layer control (set True if you want a toggle)
    overlay=True
)

folium.GeoJson(
    country_gdf,   # <-- IMPORTANT: all countries, not plot_data
    name="Unselected mask",
    style_function=lambda feature: (
        {
            "fillColor": "black",
            "color": "white",
            "weight": 0.3,
            "fillOpacity": 0.25,
        }
        if feature["properties"].get("code_alpha3") not in selected_a3
        else {
            # selected countries: make the mask transparent so your choropleth shows
            "fillColor": "transparent",
            "color": "transparent",
            "weight": 0,
            "fillOpacity": 0.0,
        }
    ),
).add_to(fg_unselected)

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

if ctr_filter_crit == "Average Level":
    active_fgs = [base, fg_unselected, fg_mean]
    cm_mean.add_to(m)
else:
    active_fgs = [base, fg_unselected, fg_std]
    cm_std.add_to(m)

with map_panel:
    map_data = st_folium(
            m, 
            use_container_width = True, 
            feature_group_to_add=active_fgs,
            layer_control=None,
    )

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

    # st.write(f"**{outcome_var_mapper[outcome_var_selection]} ({'Average' if ctr_filter_crit == 'Average Level' else 'Opinion Heterogeneity'}):** {current_value:.2f}")#st.write(f"{outcome_var_mapper[outcome_var_selection]} ({ctr_filter_crit}): {current_value:.2f}")

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
        "SciConsens": {
            "title": "Scientific Consensus",
            "description": "Informs participants that '99% of expert climate scientists agree that the Earth is warming, and climate change is happening, mainly because of human activity'."
        },
    }

    intervention_details = interventions.get(best_intervention, {})
    full_name = intervention_details.get("title", best_intervention)
    description = intervention_details.get("description", "No detailed information available for this intervention.")

    st.write(f"Best psychological intervention to promote this metric in {country_name}: **{full_name}**")

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
        s = survey_data.loc[survey_data["alpha3"] == country_code_a3, outcome_var_selection].dropna().copy()

        if outcome_var_selection == "share_sm":
            s = s[s.isin([0, 1])]
            plot_data = s.map({0: "No", 1: "Yes"})

        elif outcome_var_selection == "wept":
            plot_data = pd.to_numeric(s, errors="coerce").round(0).astype("Int64").astype(str)
        else:
            plot_data = s  # continuous variables stay continuous
        
        fig = px.histogram(
            x=plot_data,
            title=f"Distribution of {outcome_var_mapper[outcome_var_selection]} in {country_name}",
            labels={"x": outcome_var_mapper[outcome_var_selection]},
        )
        if outcome_var_selection == "share_sm":
            fig.update_xaxes(type="category")

        st.plotly_chart(fig, use_container_width=True)
    else:
        if outcome_var_selection in ["belief_cc", "policy_support"]:

            if group_selection == "age":
                df = survey_data.loc[
                    survey_data["alpha3"] == country_code_a3,
                    [outcome_var_selection, "age"]
                ].dropna().copy()

                df["group_bins"] = pd.cut(
                        df["age"],
                        bins=[-float("inf"), 34, 54, float("inf")],
                        labels=["18-34", "35-54", "55+"]
                    )
                x = df[outcome_var_selection].astype(float)
                xgrid = np.linspace(x.min(), x.max(), 300)

                fig = go.Figure()
                for g in ["18-34", "35-54", "55+"]:
                    vals = df.loc[df["group_bins"] == g, outcome_var_selection].astype(float).values
                    if len(vals) < 3 or np.std(vals) == 0:
                        continue
                    y = gaussian_kde(vals)(xgrid)
                    fig.add_trace(go.Scatter(x=xgrid, y=y, mode="lines", fill="tozeroy", name=g, opacity=0.45))

                fig.update_layout(
                    title=f"Distribution of {outcome_var_mapper[outcome_var_selection]} in {country_name}",
                    xaxis_title=outcome_var_mapper[outcome_var_selection],
                    yaxis_title="Density",
                    template="plotly_white",
                    legend=dict(
                        x=0.01, y=0.99,
                        xanchor="left", yanchor="top"
                    )
                )
                st.plotly_chart(fig, use_container_width=True)

            elif group_selection == "gender":
                df = survey_data.loc[
                    survey_data["alpha3"] == country_code_a3,
                    [outcome_var_selection, "gender"]
                ].dropna().copy()

                df = df[df["gender"].isin([1, 2])]
                df["gender_label"] = df["gender"].map({1: "Male", 2: "Female"})
                df = df[df["gender_label"].notna()]

                x = df[outcome_var_selection].astype(float)
                xgrid = np.linspace(x.min(), x.max(), 300)

                fig = go.Figure()
                for g in ["Male", "Female"]:
                    vals = df.loc[df["gender_label"] == g, outcome_var_selection].astype(float).values
                    if len(vals) < 3 or np.std(vals) == 0:
                        continue
                    y = gaussian_kde(vals)(xgrid)
                    fig.add_trace(go.Scatter(x=xgrid, y=y, mode="lines", fill="tozeroy", name=g, opacity=0.45))

                fig.update_layout(
                    title=f"Distribution of {outcome_var_mapper[outcome_var_selection]} in {country_name} (by Gender)",
                    xaxis_title=outcome_var_mapper[outcome_var_selection],
                    yaxis_title="Density",
                    template="plotly_white",
                    legend=dict(
                        x=0.01, y=0.99,
                        xanchor="left", yanchor="top"
                    )
                )
                st.plotly_chart(fig, use_container_width=True)

            elif group_selection == "education_level":
                df = survey_data.loc[
                    survey_data["alpha3"] == country_code_a3,
                    [outcome_var_selection, "education_level"]
                ].dropna().copy()

                df["edu_label"] = df["education_level"].map({
                    1: "Up to high school",
                    2: "Up to high school",
                    3: "College",
                    4: "Postgraduate and higher",
                    5: "Postgraduate and higher",
                })
                df = df[df["edu_label"].notna()]

                x = df[outcome_var_selection].astype(float)
                xgrid = np.linspace(x.min(), x.max(), 300)

                fig = go.Figure()
                for g in ["Up to high school", "College", "Postgraduate and higher"]:
                    vals = df.loc[df["edu_label"] == g, outcome_var_selection].astype(float).values
                    if len(vals) < 3 or np.std(vals) == 0:
                        continue
                    y = gaussian_kde(vals)(xgrid)
                    fig.add_trace(go.Scatter(x=xgrid, y=y, mode="lines", fill="tozeroy", name=g, opacity=0.45))

                fig.update_layout(
                    title=f"Distribution of {outcome_var_mapper[outcome_var_selection]} in {country_name} (by Education)",
                    xaxis_title=outcome_var_mapper[outcome_var_selection],
                    yaxis_title="Density",
                    template="plotly_white",
                    legend=dict(
                        x=0.01, y=0.99,
                        xanchor="left", yanchor="top"
                    )
                )
                st.plotly_chart(fig, use_container_width=True)

            else:  # income_level
                df = survey_data.loc[
                    survey_data["alpha3"] == country_code_a3,
                    [outcome_var_selection, "income_level"]
                ].dropna().copy()

                df["income_level"] = pd.to_numeric(df["income_level"], errors="coerce")

                df["income_label"] = df["income_level"].map({
                    1: "Up to 15k",
                    2: "Up to 15k",
                    3: "15k–25k",
                    4: "25k+",
                    5: "25k+",
                    6: "25k+",
                    7: "25k+",
                    8: "25k+",
                })
                df = df[df["income_label"].notna()]

                x = df[outcome_var_selection].astype(float)
                xgrid = np.linspace(x.min(), x.max(), 300)

                fig = go.Figure()
                for g in ["Up to 15k", "15k–25k", "25k+"]:
                    vals = df.loc[df["income_label"] == g, outcome_var_selection].astype(float).values
                    if len(vals) < 3 or np.std(vals) == 0:
                        continue
                    y = gaussian_kde(vals)(xgrid)
                    fig.add_trace(go.Scatter(x=xgrid, y=y, mode="lines", fill="tozeroy", name=g, opacity=0.45))

                fig.update_layout(
                    title=f"Distribution of {outcome_var_mapper[outcome_var_selection]} in {country_name} (by Income)",
                    xaxis_title=outcome_var_mapper[outcome_var_selection],
                    yaxis_title="Density",
                    template="plotly_white",
                    legend=dict(
                        x=0.01, y=0.99,
                        xanchor="left", yanchor="top"
                    )
                )
                st.plotly_chart(fig, use_container_width=True)

        else:
        # outcome is share_sm or wept -> matrix bubble plot
            if group_selection == "age":
                df = survey_data.loc[
                    survey_data["alpha3"] == country_code_a3,
                    ["age", outcome_var_selection]
                ].dropna().copy()

                df["age_bin"] = pd.cut(
                    df["age"],
                    bins=[-float("inf"), 34, 54, float("inf")],
                    labels=["18-34", "35-54", "55+"]
                )

                if outcome_var_selection == "share_sm":
                    df = df[df[outcome_var_selection].isin([0, 1])]

                counts = df.groupby(["age_bin", outcome_var_selection]).size().reset_index(name="n")

                if outcome_var_selection == "share_sm":
                    counts[outcome_var_selection] = counts[outcome_var_selection].map({0: "No", 1: "Yes"})
                else:
                    counts[outcome_var_selection] = counts[outcome_var_selection].astype(int).astype(str)
                if outcome_var_selection == "share_sm":

                    fig = px.scatter(
                        counts,
                        x=outcome_var_selection,
                        y="age_bin",
                        size="n",
                        size_max=45,
                        labels={"n": "N", "age_bin": "Age group", outcome_var_selection: outcome_var_mapper[outcome_var_selection]},
                    )
                    fig.update_traces(marker=dict(opacity=0.9))
                    fig.update_layout(template="plotly_white")
                else:
                    v = pd.to_numeric(df[outcome_var_selection], errors="coerce").round(0)
                    df["outcome_cat"] = v.astype("Int64").astype(str)
                    cats = sorted(df["outcome_cat"].dropna().unique(), key=lambda x: int(x))
                    category_order = cats

                    fig = px.histogram(
                        df,
                        x="outcome_cat",
                        facet_row="age_bin",
                        category_orders={
                            "age_bin": ["18-34", "35-54", "55+"],
                            "outcome_cat": category_order
                        },
                        labels={
                            "outcome_cat": outcome_var_mapper[outcome_var_selection],
                            "age_group": ""
                        },
                        title="WEPT by Age"
                        )
                    fig.update_layout(template="plotly_white")
                    fig.update_yaxes(title_text="",  showticklabels=False)
                    fig.update_xaxes(type="category")
                    # move facet labels to the left & clean the text
                    for a in fig.layout.annotations:
                        if "age_bin=" in a.text:
                            a.text = a.text.replace("age_bin=", "")
                            a.x = -0.06
                            a.xanchor = "right"
                            a.textangle = 0 
                    fig.update_layout(margin=dict(l=60))

                st.plotly_chart(fig, use_container_width=True)

            elif group_selection == "gender":
                df = survey_data.loc[
                    survey_data["alpha3"] == country_code_a3,
                    ["gender", outcome_var_selection]
                ].dropna().copy()

                df = df[df["gender"].isin([1, 2])]
                df["gender_label"] = df["gender"].map({1: "Male", 2: "Female"})
                df = df[df["gender_label"].notna()]

                if outcome_var_selection == "share_sm":
                    df = df[df[outcome_var_selection].isin([0, 1])]

                counts = df.groupby(["gender_label", outcome_var_selection]).size().reset_index(name="n")

                if outcome_var_selection == "share_sm":
                    counts[outcome_var_selection] = counts[outcome_var_selection].map({0: "No", 1: "Yes"})
                else:
                    counts[outcome_var_selection] = counts[outcome_var_selection].astype(int).astype(str)

                fig = px.scatter(
                    counts,
                    x=outcome_var_selection,
                    y="gender_label",
                    size="n",
                    size_max=45,
                    labels={"n": "N", "gender_label": "Gender", outcome_var_selection: outcome_var_mapper[outcome_var_selection]},
                )
                fig.update_traces(marker=dict(opacity=0.9))
                fig.update_layout(template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

            elif group_selection == "education_level":
                df = survey_data.loc[
                    survey_data["alpha3"] == country_code_a3,
                    [outcome_var_selection, "education_level"]
                ].dropna().copy()

                if outcome_var_selection == "share_sm":
                    df = df[df[outcome_var_selection].isin([0, 1])]

                df["edu_label"] = df["education_level"].map({
                    1: "High school",
                    2: "High school",
                    3: "College",
                    4: "Postgrad+",
                    5: "Postgrad+",
                })
                df = df[df["edu_label"].notna()]

                # counts per cell
                counts = df.groupby([outcome_var_selection, "edu_label"]).size().reset_index(name="n_cell")
                group_sizes = df.groupby("edu_label").size().reset_index(name="n_group")
                counts = counts.merge(group_sizes, on="edu_label", how="left")

                if outcome_var_selection == "share_sm":
                    counts[outcome_var_selection] = counts[outcome_var_selection].map({0: "No", 1: "Yes"})
                else:
                    counts[outcome_var_selection] = counts[outcome_var_selection].astype(int).astype(str)

                edu_order = ["High school", "College", "Postgrad+"]

                if outcome_var_selection == "share_sm":
                    fig = px.scatter(
                        counts,
                        y="edu_label",
                        x=outcome_var_selection,
                        size="n_group",
                        size_max=45,
                        title=f"{outcome_var_mapper[outcome_var_selection]} by Education Level",
                        labels={
                            "edu_label": "Education level",
                            outcome_var_selection: outcome_var_mapper[outcome_var_selection],
                            "n_group": "Group size",
                            "n_cell": "Cell count",
                        },
                        category_orders={"edu_label": edu_order},
                        hover_data=["n_group", "n_cell"],
                    )
                    fig.update_traces(marker=dict(opacity=0.9))
                    fig.update_layout(template="plotly_white")

                else: #wept 
                    v = pd.to_numeric(df[outcome_var_selection], errors="coerce").round(0)
                    df["wept_cat"] = v.astype("Int64").astype(str)
                    cats = sorted(df["wept_cat"].dropna().unique(), key=lambda x: int(x))
                    wept_order = cats
                    edu_order = ["High school", "College", "Postgrad+"]

                    fig = px.histogram(
                        df,
                        x="wept_cat",
                        facet_row="edu_label",
                        category_orders={
                            "edu_label": edu_order,
                            "wept_cat": wept_order
                        },
                        labels={
                            "wept_cat": outcome_var_mapper[outcome_var_selection],
                            "edu_label": ""
                        },
                        title="WEPT by Education Level",
                    )

                    fig.update_xaxes(type="category")
                    fig.update_yaxes(title_text="", showticklabels=False)
                    for a in fig.layout.annotations:
                            a.text = a.text.replace("=", "")
                            a.x = -0.06
                            a.xanchor = "right"
                            a.textangle = 270 
                    fig.update_layout(margin=dict(l=60))      
                    fig.update_layout(template="plotly_white")                
                st.plotly_chart(fig, use_container_width=True)

            else:  # income_level
                df = survey_data.loc[
                    survey_data["alpha3"] == country_code_a3,
                    [outcome_var_selection, "income_level"]
                ].dropna().copy()

                if outcome_var_selection == "share_sm":
                    df = df[df[outcome_var_selection].isin([0, 1])]

                df["income_level"] = pd.to_numeric(df["income_level"], errors="coerce")
                df["income_label"] = df["income_level"].map({
                    1: "Up to 15k",
                    2: "Up to 15k",
                    3: "15k–25k",
                    4: "25k+",
                    5: "25k+",
                    6: "25k+",
                    7: "25k+",
                    8: "25k+",
                })
                df = df[df["income_label"].notna()]

                counts = df.groupby([outcome_var_selection, "income_label"]).size().reset_index(name="n")

                if outcome_var_selection == "share_sm":
                    counts[outcome_var_selection] = counts[outcome_var_selection].map({0: "No", 1: "Yes"})
                else:
                    counts[outcome_var_selection] = counts[outcome_var_selection].astype(int).astype(str)

                fig = px.scatter(
                    counts,
                    y="income_label",
                    x=outcome_var_selection,
                    size="n",
                    size_max=45,
                    title=f"{outcome_var_mapper[outcome_var_selection]} by Income Level",
                    labels={
                        "income_label": "Income level",
                        outcome_var_selection: outcome_var_mapper[outcome_var_selection],
                        "n": "N",
                    },
                )
                fig.update_traces(marker=dict(opacity=0.9))
                fig.update_layout(template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
