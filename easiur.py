import numpy as np
import pandas as pd 
import os, sys 

MODULE_PATH     = os.path.dirname(__file__)
EIA_GENERATOR_FILE  = os.path.join(MODULE_PATH,'data/eia8602019/3_1_Generator_Y2019.xlsx')
EIA_ENVIRO_FILE = os.path.join(MODULE_PATH,'data/eia8602019/6_2_EnviroEquip_Y2019.xlsx')
EMISSIONS_FILE = os.path.join(MODULE_PATH,'data/emissions/egrid2019_data.xlsx')
EASIUR_FILE     = os.path.join(MODULE_PATH,'data/easiur_msc/msc_per_ton_by_plant.csv')
OUTPUT_FILE     = os.path.join(MODULE_PATH,'marginalHealthCosts.csv')

DEFAULT_STACK_HEIGHT = 150 # none, 0, 150, or 300
INFLATION_RATE = 1.2 # 2010 USD to 2020 USD

def getPlants():

    # Open files
    generators = pd.read_excel(EIA_GENERATOR_FILE,skiprows=1,usecols=["Plant Code","Technology","Nameplate Capacity (MW)","Status"])
    generators = generators[generators["Status"] == 'OP']
    generators = generators[(~generators["Technology"].isin(["Solar Photovoltaic", "Nuclear", "Onshore Wind Turbine", "Offshore Wind Turbine", "Batteries",
                                                                "Conventional Hydroelectric", "Hydroelectric Pumped Storage"]))]

    # numpy
    plantCodes = np.unique(generators['Plant Code'].values.astype(int))

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

    return plantCodes, genStack

def getEmissions(plantCodes):
    emissions = pd.read_excel(EMISSIONS_FILE,sheet_name='PLNT19',skiprows=1,usecols=['ORISPL','PLNGENAN','PLNOXAN','PLSO2AN'])
    emissionsPlantCodes = emissions['ORISPL'].values.astype(int)

    generation = emissions['PLNGENAN'].values
    NOx_mtonnes = emissions['PLNOXAN'].values * .907
    SO2_mtonnes = emissions['PLSO2AN'].values * .907

    plantGeneration = np.zeros(len(plantCodes))
    SO2_emissions = np.zeros(len(plantCodes))
    NOx_emissions = np.zeros(len(plantCodes))

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
    SO2_emissions[plantGeneration < 0] = np.nan
    NOx_emissions[plantGeneration < 0] = np.nan
    plantGeneration[plantGeneration < 0] = np.nan

    return plantGeneration, SO2_emissions, NOx_emissions

def getEasiur(plantCodes, genStack, season):
    
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

def getMarginalHealthCosts(plantCodes,season='Annual',asarray=False):
    '''Get marginal health costs ($/MWh) for plants across the United States. All data processing should be done separately from this function call. This function provides an abstraction for accessing m.h.c. data from this module's underlying csv.
    
    Arguments:
    ----------
    `plantCodes` (ndarray) : Numpy array of integer plant codes
    `season` (str) : Season of underlying marginal health costs provided by EASIUR [`Annual`|`Spring`|`Summer`|`Fall`|`Winter`]

    Returns:
    ----------
    `marginalHealthCosts` (ndarray) : Numpy array of health damages ($) per generation (MWh) at a certain plant code. Plants with incomplete data return 'na' cells;
    '''

    mhc = pd.read_csv(OUTPUT_FILE,usecols=['Plant Code','Marginal Health Cost; {} ($ per MWh)'.format(season)])
    mhcPlantCodes = mhc['Plant Code'].values.astype(int)
    mhcValues = mhc['Marginal Health Cost; {} ($ per MWh)'.format(season)].values

    marginalHealthCost = np.zeros(len(plantCodes))

    for i in range(len(plantCodes)):
        if not plantCodes[i] in mhcPlantCodes:
            marginalHealthCost[i] = np.nan
        else:
            marginalHealthCost[i] = mhcValues[mhcPlantCodes == plantCodes[i]]

    if asarray:
        return marginalHealthCost
        
    return pd.DataFrame(data=marginalHealthCost, index=plantCodes, columns=['Marginal Health Cost ($/MWh)'])

def main():
    ''' Generate the CSV file of plant codes, generator IDs and MHC [$/MWh]. This should only be run as main (not from a module) in order to preserve the abstract interface :)
    '''
    if __name__ != '__main__':
        print('Run easiur.py independently (not as module) to execute this function')
        sys.exit(1)

    plants = pd.DataFrame()

    # plant data
    plants['Plant Code'], plants['Stack Height (m)'] = getPlants()
    # emissions and generation data
    plants['Annual Plant Generation (MWh)'], plants['Annual Plant SO2 Emissions (M.Tonnes)'], plants['Annual Plant NOx Emissions (M.Tonnes)'] = getEmissions(plants['Plant Code'].values)
    plants['Marginal SO2 Emissions (M.Tonnes per MWh)'] = plants['Annual Plant SO2 Emissions (M.Tonnes)']/plants['Annual Plant Generation (MWh)']
    plants['Marginal NOx Emissions (M.Tonnes per MWh)'] = plants['Annual Plant NOx Emissions (M.Tonnes)']/plants['Annual Plant Generation (MWh)']
    # marginal easiur costs
    plants['Marginal Emissions Damages SO2; Annual ($ per M.Tonne)'], plants['Marginal Emissions Damages NOx; Annual ($ per M.Tonne)'] = getEasiur(plants['Plant Code'], plants['Stack Height (m)'], 'Annual')
    plants['Marginal Emissions Damages SO2; Spring ($ per M.Tonne)'], plants['Marginal Emissions Damages NOx; Spring ($ per M.Tonne)'] = getEasiur(plants['Plant Code'], plants['Stack Height (m)'], 'Spring')
    plants['Marginal Emissions Damages SO2; Summer ($ per M.Tonne)'], plants['Marginal Emissions Damages NOx; Summer ($ per M.Tonne)'] = getEasiur(plants['Plant Code'], plants['Stack Height (m)'], 'Summer')
    plants['Marginal Emissions Damages SO2; Fall ($ per M.Tonne)'], plants['Marginal Emissions Damages NOx; Fall ($ per M.Tonne)'] = getEasiur(plants['Plant Code'], plants['Stack Height (m)'], 'Fall')
    plants['Marginal Emissions Damages SO2; Winter ($ per M.Tonne)'], plants['Marginal Emissions Damages NOx; Winter ($ per M.Tonne)'] = getEasiur(plants['Plant Code'], plants['Stack Height (m)'], 'Winter')
    # marginal health costs
    plants['Marginal Health Cost; Annual ($ per MWh)'] = plants['Marginal Emissions Damages SO2; Annual ($ per M.Tonne)']*plants['Marginal SO2 Emissions (M.Tonnes per MWh)'] + plants['Marginal Emissions Damages NOx; Annual ($ per M.Tonne)']*plants['Marginal NOx Emissions (M.Tonnes per MWh)']
    plants['Marginal Health Cost; Spring ($ per MWh)'] = plants['Marginal Emissions Damages SO2; Spring ($ per M.Tonne)']*plants['Marginal SO2 Emissions (M.Tonnes per MWh)'] + plants['Marginal Emissions Damages NOx; Spring ($ per M.Tonne)']*plants['Marginal NOx Emissions (M.Tonnes per MWh)']
    plants['Marginal Health Cost; Summer ($ per MWh)'] = plants['Marginal Emissions Damages SO2; Summer ($ per M.Tonne)']*plants['Marginal SO2 Emissions (M.Tonnes per MWh)'] + plants['Marginal Emissions Damages NOx; Summer ($ per M.Tonne)']*plants['Marginal NOx Emissions (M.Tonnes per MWh)']
    plants['Marginal Health Cost; Fall ($ per MWh)'] = plants['Marginal Emissions Damages SO2; Fall ($ per M.Tonne)']*plants['Marginal SO2 Emissions (M.Tonnes per MWh)'] + plants['Marginal Emissions Damages NOx; Fall ($ per M.Tonne)']*plants['Marginal NOx Emissions (M.Tonnes per MWh)']
    plants['Marginal Health Cost; Winter ($ per MWh)'] = plants['Marginal Emissions Damages SO2; Winter ($ per M.Tonne)']*plants['Marginal SO2 Emissions (M.Tonnes per MWh)'] + plants['Marginal Emissions Damages NOx; Winter ($ per M.Tonne)']*plants['Marginal NOx Emissions (M.Tonnes per MWh)']
    
    
    # save to file
    plants.to_csv(OUTPUT_FILE)

if __name__ == '__main__':
    main()
