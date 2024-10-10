import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from sqlalchemy import create_engine
from streamlit_folium import st_folium
from folium.features import GeoJsonTooltip

# Database connection
engine = create_engine('postgresql://dio:your_password@localhost/census_data')

# Define titles for each census code
census_titles = {
    'TS001': 'Number of usual residents in households and communal establishments',
    'TS002': 'Legal partnership status',
    'TS003': 'Household composition',
    'TS004': 'Country of birth',
    'TS005': 'Passports held',
    'TS006': 'Population density',
    'TS008': 'Sex'
}

# Streamlit app
st.set_page_config(page_title="UK Census Data 2021", layout="wide")
st.title("UK Census Data 2021")

# Custom CSS for styling
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
    }
    .stTextInput > div > div > input {
        border: 1px solid #ccc;
        border-radius: 4px;
    }
    .stDataFrame {
        border: 1px solid #ddd;
        border-radius: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

# Input section
st.markdown("### Enter a UK Postcode to view census data and map visualization:")
postcode = st.text_input("Postcode:", placeholder="e.g., SW1A 1AA")

if postcode:
    # Retrieve postcode data
    query = f"SELECT * FROM postcode_data WHERE pcd = '{postcode}'"
    postcode_data = pd.read_sql(query, engine)

    if not postcode_data.empty:
        lat, long, oa21 = postcode_data.iloc[0][['lat', 'long', 'oa21']]

        # Display map
        m = folium.Map(location=[lat, long], zoom_start=14)
        folium.Marker([lat, long], popup=postcode, icon=folium.Icon(color='red')).add_to(m)

        # Retrieve output area and adjoining areas
        oa_query = f"""
        SELECT * FROM output_areas
        WHERE ST_Touches(geometry, (SELECT geometry FROM output_areas WHERE oa21cd = '{oa21}'))
        OR oa21cd = '{oa21}'
        """
        oa_data = gpd.read_postgis(oa_query, engine, geom_col='geometry')

        # Add output areas to map with hover text
        folium.GeoJson(
            oa_data,
            tooltip=GeoJsonTooltip(fields=['oa21cd', 'lsoa21cd', 'lsoa21nm'],
                                   aliases=['OA Code:', 'LSOA Code:', 'LSOA Name:']),
            style_function=lambda x: {'color': 'blue', 'weight': 2, 'fillOpacity': 0.1}
        ).add_to(m)

        # Display map
        st_folium(m, width=700, height=500)

        # Retrieve and display census data for all relevant output areas
        oa_codes = tuple(oa_data['oa21cd'].tolist())
        census_query = f"SELECT * FROM census_data WHERE geography_code IN {oa_codes}"
        census_data = pd.read_sql(census_query, engine)

        # Group by census code and display data
        for census_code, group in census_data.groupby('census_code'):
            title = census_titles.get(census_code, 'Unknown Census Data')
            st.markdown(f"#### {census_code} - {title}")

            # Concatenate data for the same census code
            combined_data = pd.DataFrame()
            for _, row in group.iterrows():
                data_df = pd.json_normalize(row['data'])
                data_df.insert(0, 'Output Area', row['geography_code'])
                combined_data = pd.concat([combined_data, data_df], ignore_index=True)

            # Style the DataFrame
            styled_df = combined_data.style.set_properties(**{
                'background-color': '#f9f9f9',
                'border-color': 'black',
                'border-style': 'solid',
                'border-width': '1px',
                'color': 'black',
                'font-size': '12px'
            }).highlight_max(axis=0, color='lightgreen')

            # Display the styled DataFrame
            st.dataframe(styled_df)

    else:
        st.error("Postcode not found.")
else:
    st.info("Please enter a valid UK postcode to proceed.")