import streamlit as st
import pandas as pd
import geopandas as gpd
import branca

def reset_all_filters():
    st.session_state["num_ctr_filter"] = 63
    st.session_state["top_bottom"] = "Top"
    
    if "countries_to_display" in st.session_state:
        del st.session_state["countries_to_display"]

def reset_multiselect():
    if "countries_to_display" in st.session_state:
        del st.session_state["countries_to_display"]


### Data loading and processing ################################################################
@st.cache_data
def read_gpd(path):
    gdf = gpd.read_file(path)
    return gdf

@st.cache_data
def load_data(path):
    df = pd.read_csv(path)

    for col in df.columns:
        if df[col].dtype in ['float32', 'float64']:
            df[col] = round(df[col], 2)
    return df



@st.cache_data
def merge_country_data(_geo, aggs, basics):
    merge1 = _geo.merge(
        aggs, 
        left_on="id",
        right_on="alpha3",
        how="right"
    )
    merge_2 = merge1.merge(
        basics, 
        left_on="id", 
        right_on="code_alpha3", 
        how="left"
    )
    return merge_2

"""
@st.cache_data
def get_country_aggregates(df):
    mean = df[df["intervention"] == "control"]\
        .groupby("country_code")[["belief_cc", "policy_support", "share_sm", "wept"]]\
        .mean().reset_index()
    std = df[df["intervention"] == "control"]\
        .groupby("country_code")[["belief_cc", "policy_support", "share_sm", "wept"]]\
        .std().reset_index()
    return pd.concat([mean, std], keys=["mean", "std"], names=["stat"]).reset_index(level="stat")
"""

@st.cache_data
def mean_disp_split(_gdf):
    mean_data = _gdf[[
        "name", "geometry",
        "belief_cc_mean", "policy_support_mean", "share_social_media_mean", "wept_mean"
        ]].rename(columns={
            "belief_cc_mean": "belief_cc",
            "policy_support_mean": "policy_support",
            "share_social_media_mean": "share_sm",
            "wept_mean": "wept"
        })
    disp_data = _gdf[[
        "name", "geometry",
        "belief_cc_std", "policy_support_std", "share_social_media_entropy", "wept_std"
        ]].rename(columns={
            "belief_cc_std": "belief_cc",
            "policy_support_std": "policy_support",
            "share_social_media_entropy": "share_sm",
            "wept_std": "wept"
        })
    return mean_data, disp_data
#######################################################################################################

### Data filters ################################################################################
@st.cache_data
def filter_survey_data(
    df, age, gender, education, income, perc_ses, sp_ideology, econ_ideology
):
    filtered = df[
        (df["age"] >= age[0]) & (df["age"] <= age[1]) &
        (df["gender"].isin(gender)) &
        (df["education"].isin(education)) &
        (df["income"].isin(income)) &
        (df["perc_ses"].isin(perc_ses)) &
        (df["sp_ideology"] >= sp_ideology[0]) & (df["sp_ideology"] <= sp_ideology[1]) &
        (df["econ_ideology"] >= econ_ideology[0]) & (df["econ_ideology"] <= econ_ideology[1])
    ]
    return filtered

#@st.cache_data # Caching causes aggregates to not update properly
def update_country_data(
    _df, 
    outcome_var, 
    crit, 
    num, 
    top_bottom,):
    if crit is None:
        return _df
    if crit == "Average levels":
        df_stat = mean_disp_split(_df)[0]
    else:
        df_stat = mean_disp_split(_df)[1]
    sorted_df = df_stat.sort_values(by=outcome_var, ascending=(top_bottom == "Bottom"))
    selected_countries = sorted_df.head(num)["name"].tolist()
    updated_df = _df[_df["name"].isin(selected_countries)]
    return updated_df
#######################################################################################################

### Colormap generation ##############################################################################
@st.cache_data
def generate_colormaps(sel_var, _country_gdf, outcome_var_mapper, mean_mapper, disp_mapper):

    cm_mean = branca.colormap.LinearColormap(
        vmin=_country_gdf[mean_mapper[sel_var]].quantile(0.0),
        vmax=_country_gdf[mean_mapper[sel_var]].quantile(1.0),
        colors=branca.colormap.linear.RdYlGn_05.colors,
        caption=f"Average {outcome_var_mapper[sel_var]}",
    )
    cm_std = branca.colormap.LinearColormap(
        vmin=_country_gdf[disp_mapper[sel_var]].quantile(0.0),
        vmax=_country_gdf[disp_mapper[sel_var]].quantile(1.0),
        colors=branca.colormap.linear.RdYlGn_05.colors[::-1],
        caption=f"Heterogeneity in {outcome_var_mapper[sel_var]}",
    )
    return cm_mean, cm_std
#######################################################################################################
