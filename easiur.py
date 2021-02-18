import numpy as np
import pandas as pd 
import os, sys 

MODULE_PATH     = os.path.dirname(__file__)
EIA_GEN_FILE    = os.path.join(MODULE_PATH,'data/eia8602019/3_1_Generator_Y2019.xlsx')
EIA_ENVIRO_FILE = os.path.join(MODULE_PATH,'data/eia8602019/6_2_EnviroEquip_Y2019.xlsx')
EASIUR_FILE     = os.path.join(MODULE_PATH,'data/easiur_msc/msc_by_plants')
EMISSIONS_FILE  = os.path.join(MODULE_PATH,'data/emissions/emissions2019.xlsx')

def getGenerators():

    # Open files
    generators = pd.read_excel(EIA_GEN_FILE,skiprows=1,usecols=["Plant Code","Generator ID","Technology",
                                                                "Nameplate Capacity (MW)","Status"])

    # filtering
    generators = generators[(generators["Status"] == "OP")]
    generators = generators[(~generators["Technology"].isin(["Solar Photovoltaic", "Onshore Wind Turbine", "Offshore Wind Turbine", "Batteries"]))]
    
    plantCodes = generators['Plant Code'].values.astype(int)
    genIDs = generators['Generator ID'].values
    genNameplate = generators['Nameplate Capacity (MW)'].values.astype(float)
    genNormalizedNameplate = np.zeros(len(plantCodes))

    # get percentage of plant generation
    for i in range(len(genNameplate)):
        genNormalizedNameplate[i] = genNameplate[i] / np.sum(genNameplate[plantCodes == plantCodes[i]])

    # get stack height (m)
    genStack = np.zeros(len(plantCodes))

    stacks = pd.read_excel(EIA_ENVIRO_FILE,skiprows=1,sheet_name='Stack Flue',usecols=['Plant Code','Stack Height (Feet)'])

    # fill missing
    stacks['Stack Height (Feet)'].where(stacks['Stack Height (Feet)'].astype(str) != ' ', 0, inplace=True)

    # map back to availabe plants
    stackPlants = stacks['Plant Code'].values.astype(int)
    stackHeights = stacks['Stack Height (Feet)'].values.astype(float)
    for i in range(len(plantCodes)):
        try: 
            genStack[i] = np.average(stackHeights[stackPlants == plantCodes[i]])*.3048
        except(ZeroDivisionError):
            genStack[i] = 0

    return plantCodes, genIDs, genNameplate, genNormalizedNameplate, genStack

def getMarginalCosts(plantCodes, genIDs):
    margCost = None 

    return margCost

def getEmissionsImpl(plantCodes, species):
    emissions = pd.read_excel(EMISSIONS_FILE,sheet_name=species,skiprows=1,usecols=['Plant Code','Metric Tonnes of {} Emissions'.format(species)])
    emissionsPlantCodes = emissions['Plant Code'].values[:-2].astype(int) # ignore the two information cells at the bottom
    emissions = emissions['Metric Tonnes of {} Emissions'.format(species)].values.astype(float)

    # map to plants
    plantEmissions = np.zeros(len(plantCodes))
    for i in range(len(plantCodes)):
        if plantCodes[i] in emissionsPlantCodes:
            plantEmissions[i] = np.sum(emissions[emissionsPlantCodes == plantCodes[i]])
        else:
            plantEmissions[i] = 0
    return plantEmissions

def getEmissions(plantCodes):
    emissions = pd.read_excel(EMISSIONS_FILE,sheet_name='SO2',skiprows=1,usecols=['Plant Code','Generation (kWh)'])
    emissions = emissions[emissions['Plant Code'].str.contains()] a;ljdf;lakjdf;lkadf;ljks
    generationPlantCodes = emissions['Plant Code'].values.astype(int) # ignore the two information cells at the bottom
    generation = emissions['Generation (kWh)'].values.astype(float)/1e3

    # map to plants
    plantGeneration = np.zeros(len(plantCodes))
    for i in range(len(plantCodes)):
        if plantCodes[i] in generationPlantCodes:
            plantGeneration[i] = np.sum(generation[generationPlantCodes == plantCodes[i]])
        else:
            plantGeneration[i] = 0

    return plantGeneration, getEmissionsImpl(plantCodes, 'SO2'), getEmissionsImpl(plantCodes, 'NOx')

def getEasiur(plantCodes, genStack, inflationRate=1.2):
    genStack = np.where(genStack < 75, 0, genStack)
    genStack = np.where(np.logical_and(genStack >= 75, genStack <225),150, genStack)
    genStack = np.where(genStack >= 225, 300, genStack)

    margCostPerTonSO2 = None
    margCostPerTonNOX = None

    return margCostPerTonSO2 * inflationRate, margCostPerTonNOX * inflationRate

def main():
    ''' Generate CSV file of plant codes, generator IDs and MSC [$/MWh]. 
    '''
    if __name__ != '__main__':
        print('Run easiur.py independently (not as module) to execute this function')
        sys.exit(1)

    gens = pd.DataFrame()

    gens['Plant Code'], gens['Generator ID'], gens['Nameplate Capacity (MW)'], gens['Plant-Normalized Capacity'], gens['Stack Height (m)'] = getGenerators()
    gens['Annual Plant Generation (MWh)'], gens['Annual Plant SO2 Emissions (M.Tons)'], gens['Annual Plant NOX Emissions (M.Tons)'] = getEmissions(gens['Plant Code'].values)
    gens['Marginal SO2 Emissions (M.Tons per MWh)'] = gens['Annual Plant SO2 Emissions (M.Tons)']/gens['Annual Plant Generation (MWh)']*gens['Plant-Normalized Capacity']
    #gens['marginalCostPerTonSO2'], gens['marginalCostPerTonNOX'] = getEasiur(gens['plant'],gens['stack'])
    gens.to_csv('tmp.csv')

if __name__ == '__main__':
    main()
