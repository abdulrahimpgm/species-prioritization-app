# -*- coding: utf-8 -*-
"""
Created on Wed Dec 17 11:46:07 2025

@author: Abdul Rahim
"""

import streamlit as st
import pandas as pd
from io import BytesIO

# ---------------------------------------------------
# Scoring function (DIRECT TRANSLATION from R)
# ---------------------------------------------------
def score_species(df):

    df = df.copy()

    df["IUCN_Score"] = df["IUCN_Status"].map({
        "Critically Endangered": 5,
        "Endangered": 4,
        "Vulnerable": 3,
        "Near Threatened": 2,
        "Least Concern": 1
    }).fillna(0) * 3

    df["Endemism_Score"] = df["Endemism"].map({
        "Yes": 2,
        "No": 1
    }).fillna(0) * 2

    df["Threat_Score"] = df["Threat_Level"] * 3

    df["Altitude_Score"] = df["Altitudinal_Range"].map({
        "<500": 4,
        "501-1000": 3,
        "1001-1500": 2,
        ">1500": 1
    }).fillna(0) * 1

    df["Exploitation_Score"] = df["Exploitation"].map({
        "Not exploited": 1,
        "Local use": 2,
        "Commercial use": 3
    }).fillna(0) * 2

    df["Habitat_Score"] = df["Habitat_Specificity"].apply(
        lambda x: 4 if x == 1 else 3 if x == 2 else 2 if x == 3 else 1
    ) * 1.5

    df["Use_Score"] = df["Use_Value"].apply(
        lambda x: 1 if x == 0 else 2 if x == 1 else 3 if x == 2 else 4 if x == 3 else 5
    ) * 1.5

    df["Total_Score"] = (
        df["IUCN_Score"] +
        df["Endemism_Score"] +
        df["Threat_Score"] +
        df["Altitude_Score"] +
        df["Exploitation_Score"] +
        df["Habitat_Score"] +
        df["Use_Score"]
    )

    df["Priority"] = df["Total_Score"].apply(
        lambda x: "Critical" if x >= 39 else
                  "High" if x >= 32 else
                  "Medium" if x >= 24 else
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
        df = pd.read_csv(uploaded_file)
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
        iucn = st.selectbox(
            "IUCN Status",
            ["Critically Endangered", "Endangered", "Vulnerable",
             "Near Threatened", "Least Concern"]
        )
        endemism = st.selectbox("Endemism", ["Yes", "No"])
        threat = st.slider("Threat Level (1–5)", 1, 5, 3)
        altitude = st.selectbox(
            "Altitudinal Range",
            ["<500", "501-1000", "1001-1500", ">1500"]
        )
        exploitation = st.selectbox(
            "Exploitation",
            ["Not exploited", "Local use", "Commercial use"]
        )
        habitat = st.number_input(
            "Habitat Specificity (No. of habitats)",
            min_value=1, max_value=10, value=1
        )
        use = st.number_input(
            "Use Value (No. of uses)",
            min_value=0, max_value=10, value=1
        )

        run = st.button("Prioritize")

    with col2:
        if run:
            single_df = pd.DataFrame([{
                "Species_Name": species_name,
                "IUCN_Status": iucn,
                "Endemism": endemism,
                "Threat_Level": threat,
                "Altitudinal_Range": altitude,
                "Exploitation": exploitation,
                "Habitat_Specificity": habitat,
                "Use_Value": use
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
with tabs[2]:
    st.subheader("Download Sample Files")

    sample_df = pd.DataFrame({
        "Species_Name": ["Species A", "Species B"],
        "IUCN_Status": ["Endangered", "Vulnerable"],
        "Endemism": ["Yes", "No"],
        "Threat_Level": [3, 2],
        "Altitudinal_Range": ["501-1000", "1001-1500"],
        "Exploitation": ["Local use", "Not exploited"],
        "Habitat_Specificity": [2, 1],
        "Use_Value": [2, 1]
    })

    st.download_button(
        "Download Sample CSV",
        sample_df.to_csv(index=False),
        file_name="sample_species_data.csv"
    )

    criteria_df = pd.DataFrame({
        "Criterion": [
            "IUCN Status", "Endemism", "Threat Level", "Altitudinal Range",
            "Exploitation", "Habitat Specificity", "Use Value"
        ],
        "Description": [
            "Conservation status of the species",
            "Whether the species is endemic to the region",
            "Intensity of threats faced (scale 1–5)",
            "Altitude where species occurs",
            "Level of exploitation or use",
            "Number of habitats the species occupies",
            "Number of uses by people"
        ],
        "Scoring": [
            "CR=5, EN=4, VU=3, NT=2, LC=1 (×3)",
            "Yes=2, No=1 (×2)",
            "Score 1–5 (×3)",
            "<500=4, 501-1000=3, 1001-1500=2, >1500=1 (×1)",
            "Not=1, Local=2, Commercial=3 (×2)",
            "1=4, 2=3, 3=2, >3=1 (×1.5)",
            "0=1, 1=2, 2=3, 3=4, >3=5 (×1.5)"
        ]
    })

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        criteria_df.to_excel(writer, index=False, sheet_name="Criteria")

    st.download_button(
        "Download Criteria Guide (Excel)",
        data=buffer.getvalue(),
        file_name="criteria_species_priority.xlsx"
    )
