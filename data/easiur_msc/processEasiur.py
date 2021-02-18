import pandas as pd 
import numpy as np 
import sys, os

PROGRAM_PATH = os.path.dirname(__file__)
EIA860_FOLDER = os.path.join(PROGRAM_PATH,'../eia8602019')
EIA860_PLANT_FILENAME = '2___Plant_Y2019.xlsx'
EASIUR_FILE = 'easiur_plants.csv'
OUTPUT_FILE = 'msc_per_ton_by_plant.csv'

df = pd.read_excel(os.path.join(EIA860_FOLDER,EIA860_PLANT_FILENAME), skiprows=1, usecols=['Plant Code','Latitude','Longitude'])

# Drop plants with no location
df.drop(df.index[df['Latitude'] == ' '], inplace=True)

# numpify
plantCodes = df['Plant Code'].values
lats = df['Latitude'].values
lons = df['Longitude'].values

# fix problem child
lats[plantCodes==62262] = 42.5246072

# processed dataframe
processed = pd.read_csv(os.path.join(PROGRAM_PATH,EASIUR_FILE))
processed['Plant Code'] = plantCodes

# Check
for i in range(len(plantCodes)):
    assert(int(lats[i]) == int(processed.at[i,'Latitude']))
    assert(int(lons[i]) == int(processed.at[i,'Longitude']))


# Remove plants with no data
processed.drop(processed.index[pd.isna(processed['PM25 Annual Ground'])],inplace=True)

# Reorder
cols = processed.columns.tolist()
cols.remove('Plant Code')
cols.insert(0,'Plant Code')
processed = processed[cols]

# Save to file
processed.to_csv(os.path.join(PROGRAM_PATH,OUTPUT_FILE))