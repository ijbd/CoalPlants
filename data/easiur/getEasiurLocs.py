import pandas as pd 
import numpy as np 
import os, sys 

PROGRAM_PATH = os.path.dirname(__file__)
EIA860_FOLDER = os.path.join(PROGRAM_PATH,'../eia8602019')
EIA860_PLANT_FILENAME = '2___Plant_Y2019.xlsx'
OUTPUT_FILE = 'plants.csv'

df = pd.read_excel(os.path.join(EIA860_FOLDER,EIA860_PLANT_FILENAME), skiprows=1, usecols=['Plant Code','Latitude','Longitude'])

# Drop plants with no location
df.drop(df.index[df['Latitude'] == ' '], inplace=True)

# numpify
plantCodes = df['Plant Code'].values
lats = df['Latitude'].values
lons = df['Longitude'].values

# fix problem child
lats[plantCodes==62262] = 42.5246072

with open(os.path.join(PROGRAM_PATH,OUTPUT_FILE), 'w') as f:
    for i in range(len(lats)):
        f.write(','.join([str(lons[i]),str(lats[i])]))
        f.write('\n')