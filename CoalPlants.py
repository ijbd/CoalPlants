import numpy as np
import pandas as pd 
import os, sys 

MODULE_PATH     = os.path.dirname(__file__)
EIA_PLANT_FILE = os.path.join(MODULE_PATH,'data/eia8602019/2___Plant_Y2019.xlsx')
EIA_GENERATOR_FILE  = os.path.join(MODULE_PATH,'data/eia8602019/3_1_Generator_Y2019.xlsx')
EIA_ENVIRO_FILE = os.path.join(MODULE_PATH,'data/eia8602019/6_2_EnviroEquip_Y2019.xlsx')
EGRID_FOLDER = os.path.join(MODULE_PATH,'data/egrid')
EASIUR_FILE     = os.path.join(MODULE_PATH,'data/easiur/msc_per_ton_by_plant.csv')

DEFAULT_STACK_HEIGHT = 150 # none, 0, 150, or 300
INFLATION_RATE = 1.2 # 2010 USD to 2020 USD

def _getStackHeight(plantCodes):
    # get stack height (m)
    genStack = np.zeros(len(plantCodes))

    stacks = pd.read_excel(EIA_ENVIRO_FILE,skiprows=1,sheet_name='Stack Flue',usecols=['Plant Code','Stack Height (Feet)'])

    # fill missing
    stacks['Stack Height (Feet)'].where(stacks['Stack Height (Feet)'].astype(str) != ' ', 0, inplace=True)

    # map back to availabe plants
    stackPlants = stacks['Plant Code'].values.astype(int)
    stackHeights = stacks['Stack Height (Feet)'].values.astype(float)
    for i in range(len(plantCodes)):
        a = stackHeights[stackPlants == plantCodes[i]]
        if len(a) > 0: 
            genStack[i] = int(np.average(a)*.3048)
        else:
            genStack[i] = np.nan

    return genStack

def _getEmissions(plantCodes, year=2019):
    # valid data years
    assert(year in [2012,2014,2016,2018,2019])

    # read data
    emissionsFilename = os.path.join(EGRID_FOLDER,'egrid{}_data.xlsx'.format(year))
    emissions = pd.read_excel(  emissionsFilename,
                                sheet_name='PLNT{}'.format(year-2000),
                                skiprows= 4 if year == 2012 else 1, # different file formatting for 2012
                                usecols=['ORISPL','PLNGENAN','PLNOXAN','PLSO2AN'])
    emissionsPlantCodes = emissions['ORISPL'].values.astype(int)

    # conversions 
    generation = emissions['PLNGENAN'].values
    NOx_mtonnes = emissions['PLNOXAN'].values * .907
    SO2_mtonnes = emissions['PLSO2AN'].values * .907

    # empty containers
    plantGeneration = np.zeros(len(plantCodes))
    SO2_emissions = np.zeros(len(plantCodes))
    NOx_emissions = np.zeros(len(plantCodes))

    # fill
    for i in range(len(plantCodes)):
        if plantCodes[i] in emissionsPlantCodes:
            plantGeneration[i] = np.sum(generation[emissionsPlantCodes == plantCodes[i]])
            NOx_emissions[i] = np.sum(NOx_mtonnes[emissionsPlantCodes == plantCodes[i]])
            SO2_emissions[i] = np.sum(SO2_mtonnes[emissionsPlantCodes == plantCodes[i]])
        else:
            plantGeneration[i] = np.nan
            NOx_emissions[i] = np.nan
            SO2_emissions[i] = np.nan

    # remove bad datum
    SO2_emissions[plantGeneration <= 0] = np.nan
    NOx_emissions[plantGeneration <= 0] = np.nan
    plantGeneration[plantGeneration <= 0] = np.nan

    return plantGeneration, SO2_emissions, NOx_emissions

def _getEmissionsMultiYearAverage(plantCodes,years,generation_only=False):
    # check for single year
    if(isinstance(years,int)):
        plantGeneration, SO2_emissions, NOx_emissions = _getEmissions(plantCodes,years)
        
        if generation_only:
            return plantGeneration

        return plantGeneration, SO2_emissions, NOx_emissions
    

    assert(isinstance(years,(list,np.ndarray,tuple)))

    # init container
    plantGeneration = np.zeros((len(years),len(plantCodes)))
    SO2_emissions = np.zeros((len(years),len(plantCodes)))
    NOx_emissions = np.zeros((len(years),len(plantCodes)))

    # fill
    for i in range(len(years)):
        plantGeneration[i], SO2_emissions[i], NOx_emissions[i] = _getEmissions(plantCodes,years[i])

    plantGeneration = np.nanmean(plantGeneration,axis=0)
    SO2_emissions = np.nanmean(SO2_emissions,axis=0)
    NOx_emissions = np.nanmean(NOx_emissions,axis=0)

    assert(len(plantGeneration) == len(plantCodes))

    if generation_only:
        return plantGeneration

    return plantGeneration, SO2_emissions, NOx_emissions
    
def _getEasiur(plantCodes, genStack, season):
    
    assert(season == 'Annual' or season == 'Spring' or season == 'Summer' or season == 'Fall' or season == 'Winter')
    assert(DEFAULT_STACK_HEIGHT == None or DEFAULT_STACK_HEIGHT == 0 or DEFAULT_STACK_HEIGHT == 150 or DEFAULT_STACK_HEIGHT == 300)

    if DEFAULT_STACK_HEIGHT is not None:
        genStack = np.where(np.isnan(genStack),DEFAULT_STACK_HEIGHT,genStack)

    # Filter
    df = pd.read_csv(EASIUR_FILE,usecols=['Plant Code', 'SO2 {} Ground'.format(season),'SO2 {} 150m'.format(season),
                                                'SO2 {} 300m'.format(season),'NOX {} Ground'.format(season),
                                                'NOX {} 150m'.format(season),'NOX {} 300m'.format(season)])
    easiurPlantCodes = df['Plant Code'].values.astype(int)
    SO2_ground = df['SO2 {} Ground'.format(season)].values
    SO2_150m = df['SO2 {} 150m'.format(season)].values
    SO2_300m = df['SO2 {} 300m'.format(season)].values
    NOx_ground = df['NOX {} Ground'.format(season)].values
    NOx_150m = df['NOX {} 150m'.format(season)].values
    NOx_300m = df['NOX {} 300m'.format(season)].values

    margCostPerTonSO2 = np.zeros(len(plantCodes))
    margCostPerTonNOx = np.zeros(len(plantCodes))

    for i in range(len(plantCodes)):
        if np.isnan(genStack[i]):
            mscSO2 = np.nan
            mscNOx = np.nan
        elif np.sum(easiurPlantCodes == plantCodes[i]) == 0:
            mscSO2 = np.nan 
            mscNOx = np.nan
        elif genStack[i] < 75:
            mscSO2 = SO2_ground[easiurPlantCodes == plantCodes[i]]
            mscNOx = NOx_ground[easiurPlantCodes == plantCodes[i]]
        elif genStack[i] < 225:
            mscSO2 = SO2_150m[easiurPlantCodes == plantCodes[i]]
            mscNOx = NOx_150m[easiurPlantCodes == plantCodes[i]]
        elif genStack[i] >= 225:
            mscSO2 = SO2_300m[easiurPlantCodes == plantCodes[i]]
            mscNOx = NOx_300m[easiurPlantCodes == plantCodes[i]]
        margCostPerTonSO2[i] = mscSO2
        margCostPerTonNOx[i] = mscNOx

    return margCostPerTonSO2 * INFLATION_RATE, margCostPerTonNOx * INFLATION_RATE

def getMarginalHealthCosts(plantCodes,season='Annual',years=2019):
    '''Get marginal health costs ($/MWh) for plants across the United States. All data processing should be done separately from this function call. This function provides an abstraction for accessing m.h.c. data from this module's underlying csv.
    
    Arguments:
    ----------
    `plantCodes` (ndarray or pd.Series) : Numpy array of integer plant codes
    `season` (str) : Season of underlying marginal health costs provided by EASIUR [`Annual`|`Spring`|`Summer`|`Fall`|`Winter`]
    `years` (int or list): OPTIONAL: Year(s) of generation/emissions data. Generation and emissions averaged over each year. Must be in {2010, 2012, 2014, 2016, 2018, 2019}.


    Returns:
    ----------
    `marginalHealthCosts` (series) : pandas series of health damages ($) per generation (MWh) at a certain plant code. Plants with incomplete data return 'na' cells. Series is indexed by plant code.
    '''
    assert(season in ['Annual','Spring','Summer','Fall','Winter'])

    if isinstance(plantCodes, pd.Series):
        plantCodes = plantCodes.values
    if isinstance(plantCodes,int):
        plantCodes = np.array([plantCodes])

    # plant data
    plantStackHeights = _getStackHeight(plantCodes)
    # emissions and generation data [MWh], [m.ton], [m.ton]
    plantGen, plantSO2Emissions, plantNOxEmissions = _getEmissionsMultiYearAverage(plantCodes,years)
    # marginal emissions [m.ton] / [MWh] [m.ton / MWh]
    plantMarginalSO2Emissions = plantSO2Emissions/plantGen
    plantMarginalNOxEmissions = plantNOxEmissions/plantGen
    # marginal emissions costs [$ / m.ton]
    plantMarginalSO2EmissionsCost, plantMarginalNOxEmissionsCost = _getEasiur(plantCodes, plantStackHeights, 'Annual')
    # marginal health costs [$ / m.ton] * [m.ton / Mwh] = [$ / MWh]
    plantMarginalHealthCost = plantMarginalSO2EmissionsCost*plantMarginalSO2Emissions + plantMarginalNOxEmissionsCost*plantMarginalNOxEmissions
            
    return pd.Series(data=plantMarginalHealthCost, index=plantCodes)

def getCoalPlants(regions):
    ''' getCoalPlants: Find all coal plants in a given NERC region of balancing authority.

    Args:
    --------
    `region` (str or list): all NERC regions or balancing authorities to include

    Return:
    --------
    `plants` (DataFrame): Dataframe of plant codes, locations, balancing authority, and NERC region; indexed by plant code.
    '''
    # handle single str region
    if isinstance(regions,str):
        regions = [regions]
    
    # open file 
    plants = pd.read_excel(EIA_PLANT_FILE,skiprows=1,usecols=['Plant Code', 'Latitude', 'Longitude','NERC Region','Balancing Authority Code'])
    generators = pd.read_excel(EIA_GENERATOR_FILE,skiprows=1,usecols=["Plant Code","Technology","Status"])

    # get plant codes in region
    if not 'ALL' in regions:
        plants = plants[plants['NERC Region'].isin(regions) | plants['Balancing Authority Code'].isin(regions)]
    plants.drop(columns=['NERC Region','Balancing Authority Code'],inplace=True)

    # filter for coal generators
    generators = generators[generators['Status'] == 'OP']
    #generators = generators[generators['Technology'].str.contains('Coal')]
    generators = generators[(~generators['Technology'].isin(["Solar Photovoltaic", "Onshore Wind Turbine", "Offshore Wind Turbine", "Batteries", "Conventional Hydroelectric", "Hydroelectric Pumped Storage", "Nuclear"]))]

    # final filter; should include only plants with coal generators in the correct region
    plants = plants[plants['Plant Code'].isin(generators['Plant Code'])]

    plants.set_index(plants['Plant Code'].values,inplace=True)

    return plants

def getPlantGeneration(plants,years=2019):
    ''' getCoalGeneration: Find annual plant generation (MWh). Return as a pandas dataframe indexed by plant code.

    Args:
    --------
    `plantCodes` (ndarray or dataframe): If Dataframe, must have column 'Plant Code'.
    `years` (int or list): OPTIONAL: Year(s) of data. If a list, annual generation is found as the mean of each year. Must be in {2010, 2012, 2014, 2016, 2018, 2019}.

    Return:
    --------
    `generation` (DataFrame): Dataframe of annual generation indexed by plant.
    '''

    if isinstance(plants, pd.Series):
        plants = plants.values
    elif isinstance(plants,int):
        plants = np.array([plants])

    plantGeneration = _getEmissionsMultiYearAverage(plants,years,generation_only=True)

    return pd.Series(data=plantGeneration,index=plants)
