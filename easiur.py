import numpy as np
import pandas as pd 
import os, sys 

MODULE_PATH = os.path.dirname(__file__)
EASIUR_FILE = os.path.join(MODULE_PATH,'data/easiur_msc/msc_by_plants')

def getEasiur(plantCodes, species=['NOX, SO2'], stackHeight='150m', inflationRate=1.2):
    ''' Get Marginal Social Costs [$/ton], as a function of plant code, pollutant species, 
    -----
    Args:
    `plantCodes` :
    `species` : 
    `stackHeight` :
    `inflationRate` :
    '''
    easiurDF = pd.read_excel(EASIUR_FILE)
    easiurMarginalCosts = easiurDF["{} Annual {}".format(species, stackHeight)]
    return easiurMarginalCosts * inflationRate


def getEmissions(unitCodes, species):

    pass

# marginalCosts [$/MWh] = SUM(NOx, SO2) { easiurMarginalCosts[$/ton] * [Annual tons] / [Annual MWh]}
def getMarginalCosts(plantCodes, unitCodes):
    getEasiur
    pass 
