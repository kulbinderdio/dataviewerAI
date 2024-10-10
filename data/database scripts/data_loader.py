
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine

# Database connection
engine = create_engine('postgresql://dio:your_password@localhost/census_data')

# Load postcode data
postcode_df = pd.read_csv('/home/dio/dev/dataviewerAI/data/ONSPD_AUG_2024/Data/ONSPD_AUG_2024_UK.csv')
postcode_df = postcode_df[['pcd', 'lat', 'long', 'oa21']]
postcode_df.to_sql('postcode_data', engine, if_exists='replace', index=False)

# Load output areas data
output_areas_gdf = gpd.read_file('/home/dio/dev/dataviewerAI/data/geo/Output_Areas_December_2021_Boundaries_EW_BFE_V9.geojson')
output_areas_gdf = output_areas_gdf[['OA21CD', 'LSOA21CD', 'LSOA21NM', 'geometry']]
output_areas_gdf.columns = ['oa21cd', 'lsoa21cd', 'lsoa21nm', 'geometry']
output_areas_gdf.to_postgis('output_areas', engine, if_exists='replace', index=False)

# Load census data
census_files = {
    'TS001': '/home/dio/dev/dataviewerAI/data/census_data/census2021-ts001-oa.csv',
    'TS002': '/home/dio/dev/dataviewerAI/data/census_data/census2021-ts002-oa.csv',
    # Add other files as needed
}

for code, file in census_files.items():
    df = pd.read_csv(file)
    df['census_code'] = code
    df['data'] = df.drop(columns=['date', 'geography', 'geography code']).apply(lambda x: x.to_json(), axis=1)
    df = df.rename(columns={'geography code': 'geography_code'})
    df[['geography_code', 'census_code', 'data']].to_sql('census_data', engine, if_exists='append', index=False)
