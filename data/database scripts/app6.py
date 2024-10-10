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

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Main", "About"])

if page == "Main":
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

    # Initialize session state for selected output area
    if 'selected_oa' not in st.session_state:
        st.session_state['selected_oa'] = None

    if postcode:
        # Retrieve postcode data
        query = f"SELECT * FROM postcode_data WHERE pcd = '{postcode}'"
        postcode_data = pd.read_sql(query, engine)

        if not postcode_data.empty:
            lat, long, oa21 = postcode_data.iloc[0][['lat', 'long', 'oa21']]

            # Retrieve output area and adjoining areas
            oa_query = f"""
            SELECT * FROM output_areas
            WHERE ST_Touches(geometry, (SELECT geometry FROM output_areas WHERE oa21cd = '{oa21}'))
            OR oa21cd = '{oa21}'
            """
            oa_data = gpd.read_postgis(oa_query, engine, geom_col='geometry')

            # Display map
            m = folium.Map(location=[lat, long], zoom_start=14)
            folium.Marker([lat, long], popup=postcode, icon=folium.Icon(color='red')).add_to(m)

            # Function to highlight selected area
            def style_function(feature):
                if feature['properties']['oa21cd'] == st.session_state['selected_oa']:
                    return {'fillColor': 'yellow', 'color': 'red', 'weight': 3, 'fillOpacity': 0.5}
                else:
                    return {'fillColor': 'blue', 'color': 'blue', 'weight': 2, 'fillOpacity': 0.1}

            # Add output areas to map with click functionality
            geojson = folium.GeoJson(
                oa_data,
                tooltip=GeoJsonTooltip(fields=['oa21cd', 'lsoa21cd', 'lsoa21nm'],
                                       aliases=['OA Code:', 'LSOA Code:', 'LSOA Name:']),
                style_function=style_function,
                highlight_function=lambda x: {'weight': 3, 'color': 'green', 'fillOpacity': 0.7},
                name="Output Areas"
            ).add_to(m)

            # Add click event to update selected output area
            def on_click(feature, **kwargs):
                st.session_state['selected_oa'] = feature['properties']['oa21cd']

            geojson.add_child(folium.GeoJsonPopup(fields=['oa21cd'], labels=False))
            geojson.add_child(folium.GeoJsonTooltip(fields=['oa21cd'], labels=False))

            # Display map
            map_data = st_folium(m, width=700, height=500)

            # Update selected output area based on click
            if map_data['last_active_drawing']:
                st.session_state['selected_oa'] = map_data['last_active_drawing']['properties']['oa21cd']

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

                # Style the DataFrame to highlight selected output area
                def highlight_selected(s):
                    return ['background-color: yellow' if s['Output Area'] == st.session_state['selected_oa'] else '' for _ in s]

                styled_df = combined_data.style.apply(highlight_selected, axis=1)

                # Display the styled DataFrame
                st.dataframe(styled_df)

                # Add a dropdown for visualization
                with st.expander("Show Bar Chart"):
                    # Extract the first column of census data for visualization
                    if not combined_data.empty:
                        first_data_column = combined_data.columns[2]
                        chart_data = combined_data[['Output Area', first_data_column]].set_index('Output Area')
                        st.bar_chart(chart_data)

        else:
            st.error("Postcode not found.")
    else:
        st.info("Please enter a valid UK postcode to proceed.")

elif page == "About":
    st.title("About")
    st.markdown("""
        ## UK Census Data 2021 Application
        This application provides interactive visualizations of the UK Census Data 2021.
        You can explore demographic information by entering a postcode and viewing the data on a map and in tables.

        ### Copyright Information
        Add your copyright information here.

        ### Contact
        For more information, contact [your-email@example.com](mailto:your-email@example.com).
    """)