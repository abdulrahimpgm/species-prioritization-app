# -*- coding: utf-8 -*-
"""
Created on Wed Dec 17 11:46:07 2025

@author: Abdul Rahim
"""

import streamlit as st
with st.sidebar:
    st.header("About")
    st.markdown("""
    **Species Prioritization App**

    **Author:** Zishan Ahmad Wani, Abdul Rahim PP 
    **Affiliation:**  King Abdullah University of Science and Technology (KAUST)- Saudi Arabia, SRM University-AP, India.   
    **Version:** v1.0  
    **Year:** 2025
    """)

import pandas as pd
from io import BytesIO
from pathlib import Path

# ---------------------------------------------------
# Scoring setup
# ---------------------------------------------------
REQUIRED_COLUMNS = [
    "Species_Name", "Endemism", "Population_size", "Site_occupancy",
    "Altitudinal_Range", "Habitat_Specificity", "Exploitation", "Threat_Level"
]

MAX_SCORE = 51  # 9 + 8 + 6 + 4 + 8 + 6 + 10

ENDEMISM_MAP = {"endemic": 3, "near endemic": 2, "non endemic": 1}
EXPLOITATION_MAP = {
    "not exploited": 1,
    "local use": 2, "local": 2,
    "commercial use": 3, "commercial": 3
}

# Range-type criteria: text categories (after cleaning) + numeric bins
# (upper bound inclusive, points) so plain numbers are scored too.
INF = float("inf")
POPULATION_MAP = {"<50": 4, "51-250": 3, "250-500": 2, "251-500": 2, ">500": 1}
POPULATION_BINS = [(50, 4), (250, 3), (500, 2), (INF, 1)]
SITE_MAP = {"1": 4, "2-5": 3, "6-10": 2, ">10": 1}
SITE_BINS = [(1, 4), (5, 3), (10, 2), (INF, 1)]
ALTITUDE_MAP = {"<500": 4, "501-1000": 3, "1001-1500": 2, ">1500": 1}
ALTITUDE_BINS = [(500, 4), (1000, 3), (1500, 2), (INF, 1)]
HABITAT_BINS = [(1, 4), (2, 3), (3, 2), (INF, 1)]


def _clean_text(x):
    return " ".join(str(x).strip().lower().replace("-", " ").split())


def _clean_range(x):
    s = str(x).strip().lower()
    for dash in ["–", "—", "−"]:
        s = s.replace(dash, "-")
    for word in ["individuals", "individual", "locations", "location",
                 "habitats", "habitat", "m", " "]:
        s = s.replace(word, "")
    return s


def _range_points(x, mapping, bins):
    if pd.isna(x):
        return None
    s = _clean_range(x)
    if s in mapping:
        return mapping[s]
    try:
        v = float(s)
    except ValueError:
        return None
    for upper, pts in bins:
        if v <= upper:
            return pts
    return None


def _points(series, func):
    return pd.to_numeric(series.apply(func), errors="coerce")


def _raw_points(df):
    """Points per criterion before weighting; NaN = value not recognised."""
    pts = pd.DataFrame(index=df.index)
    pts["Endemism"] = _points(df["Endemism"], lambda x: ENDEMISM_MAP.get(_clean_text(x)))
    pts["Population_size"] = _points(df["Population_size"], lambda x: _range_points(x, POPULATION_MAP, POPULATION_BINS))
    pts["Site_occupancy"] = _points(df["Site_occupancy"], lambda x: _range_points(x, SITE_MAP, SITE_BINS))
    pts["Altitudinal_Range"] = _points(df["Altitudinal_Range"], lambda x: _range_points(x, ALTITUDE_MAP, ALTITUDE_BINS))
    pts["Habitat_Specificity"] = _points(df["Habitat_Specificity"], lambda x: _range_points(x, {}, HABITAT_BINS))
    pts["Exploitation"] = _points(df["Exploitation"], lambda x: EXPLOITATION_MAP.get(_clean_text(x)))
    pts["Threat_Level"] = pd.to_numeric(df["Threat_Level"], errors="coerce").where(lambda s: s.between(1, 5))
    return pts


def prepare_columns(df):
    """Tidy column names (case-insensitive) and drop empty trailing columns/rows."""
    lookup = {c.lower(): c for c in REQUIRED_COLUMNS}
    df = df.rename(columns=lambda c: lookup.get(str(c).strip().lower(), str(c).strip()))
    empty_unnamed = [c for c in df.columns if c.startswith("Unnamed") and df[c].isna().all()]
    df = df.drop(columns=empty_unnamed).dropna(how="all")
    return df


def find_unrecognised(df):
    """List every cell whose value could not be scored (it would score 0)."""
    pts = _raw_points(df)
    rows = []
    for col in pts.columns:
        for i in df.index[pts[col].isna()]:
            rows.append({
                "Species_Name": str(df.loc[i, "Species_Name"]),
                "Column": col,
                "Value": str(df.loc[i, col])
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------
# Scoring function (maximum score = 51)
# ---------------------------------------------------
def score_species(df):

    df = df.copy()
    pts = _raw_points(df).fillna(0)

    df["Endemism_Score"] = pts["Endemism"] * 3
    df["Population_Score"] = pts["Population_size"] * 2
    df["Site_Occupancy_Score"] = pts["Site_occupancy"] * 1.5
    df["Altitude_Score"] = pts["Altitudinal_Range"] * 1
    df["Habitat_Score"] = pts["Habitat_Specificity"] * 2
    df["Exploitation_Score"] = pts["Exploitation"] * 2
    df["Threat_Score"] = pts["Threat_Level"] * 2

    df["Total_Score"] = (
        df["Endemism_Score"] +
        df["Population_Score"] +
        df["Site_Occupancy_Score"] +
        df["Altitude_Score"] +
        df["Habitat_Score"] +
        df["Exploitation_Score"] +
        df["Threat_Score"]
    )

    # Critical: >75% of max | High: 60-75% | Medium: 45-60% | Low: <45%
    df["Priority"] = df["Total_Score"].apply(
        lambda x: "Critical" if x > 0.75 * MAX_SCORE else
                  "High" if x >= 0.60 * MAX_SCORE else
                  "Medium" if x >= 0.45 * MAX_SCORE else
                  "Low"
    )

    return df

# ---------------------------------------------------
# Streamlit UI
# ---------------------------------------------------
st.set_page_config(page_title="Species Prioritization Tool", layout="wide")
st.title("🌿 Species Prioritization Tool")

tabs = st.tabs(["Bulk Prioritization", "Single Species Entry", "Downloads"])

# ---------------------------------------------------
# BULK PRIORITIZATION
# ---------------------------------------------------
with tabs[0]:
    st.subheader("Upload Species List")

    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

    if uploaded_file:
        try:
            raw = pd.read_csv(uploaded_file, encoding="utf-8-sig")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            raw = pd.read_csv(uploaded_file, encoding="cp1252")

        df = prepare_columns(raw)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

        if missing:
            st.error(
                "Your CSV is missing these columns: " + ", ".join(missing) +
                ". Download the sample CSV from the Downloads tab to see the expected format."
            )
        else:
            problems = find_unrecognised(df)
            if not problems.empty:
                st.warning(
                    "Some values were not recognised and were scored as 0. "
                    "Please check the spelling against the sample CSV:"
                )
                st.dataframe(problems)

            result = score_species(df)

            st.dataframe(result[["Species_Name", "Priority"]])

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                result.to_excel(writer, index=False, sheet_name="Species Prioritization")

            st.download_button(
                "Download Prioritization Report (Excel)",
                data=buffer.getvalue(),
                file_name="species_prioritization_report.xlsx"
            )

# ---------------------------------------------------
# SINGLE SPECIES ENTRY
# ---------------------------------------------------
with tabs[1]:
    st.subheader("Enter Species Details")

    col1, col2 = st.columns(2)

    with col1:
        species_name = st.text_input("Species Name")
        endemism = st.selectbox(
            "Endemism",
            ["Endemic", "Near Endemic", "Non Endemic"]
        )
        population = st.selectbox(
            "Population Size (mature individuals)",
            ["<50", "51-250", "251-500", ">500"]
        )
        site = st.number_input(
            "Site Occupancy (No. of locations)",
            min_value=1, max_value=1000, value=1
        )
        altitude = st.selectbox(
            "Altitudinal Range (m)",
            ["<500", "501-1000", "1001-1500", ">1500"]
        )
        habitat = st.number_input(
            "Habitat Specificity (No. of habitats)",
            min_value=1, max_value=10, value=1
        )
        exploitation = st.selectbox(
            "Exploitation",
            ["Not exploited", "Local use", "Commercial use"]
        )
        threat = st.slider("Threat Level (1–5)", 1, 5, 3)

        run = st.button("Prioritize")

    with col2:
        if run:
            single_df = pd.DataFrame([{
                "Species_Name": species_name,
                "Endemism": endemism,
                "Population_size": population,
                "Site_occupancy": site,
                "Altitudinal_Range": altitude,
                "Habitat_Specificity": habitat,
                "Exploitation": exploitation,
                "Threat_Level": threat
            }])

            single_result = score_species(single_df)

            st.table(single_result[["Species_Name", "Priority"]])

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                single_result.to_excel(writer, index=False, sheet_name="Single Species")

            st.download_button(
                "Download Single Report (Excel)",
                data=buffer.getvalue(),
                file_name="single_species_report.xlsx"
            )

# ---------------------------------------------------
# DOWNLOADS TAB
# ---------------------------------------------------
def offer_download(label, filename, mime):
    """Serve a file that lives in the repo, next to this script."""
    path = Path(__file__).parent / filename
    if path.exists():
        st.download_button(label, data=path.read_bytes(), file_name=filename, mime=mime)
    else:
        st.error(f"{filename} was not found in the app folder.")


with tabs[2]:
    st.subheader("Download Sample Files")

    offer_download("Download Sample CSV", "sample_species_data.csv", "text/csv")

    offer_download(
        "Download Criteria Guide (Excel)",
        "criteria_species_priority.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
