import numpy as np
import pandas as pd 
import os, sys 
from easiur import getEmissionsMultiYearAverage

MODULE_PATH     = os.path.dirname(__file__)
EIA_PLANT_FILE = os.path.join(MODULE_PATH,'data/eia8602019/2___Plant_Y2019.xlsx')
EIA_GENERATOR_FILE  = os.path.join(MODULE_PATH,'data/eia8602019/3_1_Generator_Y2019.xlsx')
GENERATION_FILE = os.path.join(MODULE_PATH,'data/egrid/egrid2019_data.xlsx')

def getCoalPlants(region):
    ''' getCoalPlants: Find all coal plants in a given NERC region of balancing authority.

    Args:
    --------
    `region` (str or list): all NERC regions or balancing authorities to include

    Return:
    --------
    `plants` (DataFrame): Dataframe of plant codes, locations, balancing authority, and NERC region; indexed by plant code.
    '''
    # handle single str region
    if isinstance(region,str):
        region = [region]
    
    # open file 
    plants = pd.read_excel(EIA_PLANT_FILE,skiprows=1,usecols=['Plant Code', 'Latitude', 'Longitude','NERC Region','Balancing Authority Code'])
    generators = pd.read_excel(EIA_GENERATOR_FILE,skiprows=1,usecols=["Plant Code","Technology","Status"])

    # get plant codes in region
    plants = plants[plants['NERC Region'].isin(region) | plants['Balancing Authority Code'].isin(region)]
    plants.drop(labels=['NERC Region','Balancing Authority Code'],inplace=True)

    # filter for coal generators
    generators = generators[generators['Status'] == 'OP']
    generators = generators[generators['Technology'].str.contains('Coal')]

    # final filter; should include only plants with coal generators in the correct region
    plants = plants[plants['Plant Code'].isin(generators['Plant Code'])]

    plants.set_index(plants['Plant Code'].values,inplace=True)


    return plants

def getPlantGeneration(plants,years):
    ''' getCoalGeneration: Find annual plant generation (MWh). Return as a pandas dataframe indexed by plant code.

    Args:
    --------
    `plantCodes` (ndarray or dataframe): If Dataframe, must have column 'Plant Code'.
    Return:
    --------
    `generation` (DataFrame): Dataframe of annual generation indexed by plant.
    '''

    if isinstance(plants, pd.DataFrame):
        plants = plants['Plant Code'].values
    elif isinstance(plants, pd.Series):
        plants = plants.values

    plantGeneration = getEmissionsMultiYearAverage(plants,years,generationOnly=True)

    return pd.DataFrame(data=plantGeneration,index=plants,columns=['Plant Generation (MWh)'])

def test():
    pass
    
if __name__ == '__main__':
    test()