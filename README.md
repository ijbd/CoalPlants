# Coal Plants Python Integration Module
Code by ijbd and dcorrell

## Updates
2/12/2021
> Gathered data for emissions, generator location, and marginal social costs. 

2/15/2021
> Fixed EASIUR processing script. Updated data source descriptions.

2/17/2021
> Worked on `easiur.py` with the goal of getting a csv to pull marginal cost per MWh for any generator in the U.S. I started by getting generator info form EIA860 including nameplate capacity and stack heights. **ASSUMPTION:** Since annual emissions/generation data are by plant, each generator in a plant has the same marginal emissions. **ASSUMPTION:** Every generator in a plant has the average height of all stacks reported for that plant. **ASSUMPTION:** Generators with no stack height data are assumed to have stack heights of 150m.

2/18/2021-2/22/2021
> Finished processing the final CSV with marginal health costs ($/MWh) for each plant. 

2/23/2021-3/1/2021
> Found a large numbers of plants without emissions data. Switched to eGRID emissions data, which has a larger number of plants, but found the same issue. **Solution:** Filtered out renewable plants. After applying that filter, the script produced valid marginal health costs for 2881 of 3372 conventional (fossil fuel) plants. 

3/11/2021-3/12/2021
> Some basic updates to maintain consistency with coal plants modular. Return pandas DataFrame and accept pandas Series of plant codes (numpy array still accepted). BEGAN PLANTS: Localized coal plant and generation data. Established interface. Finished implementation and interface. Tested with different regional inputs. **Currently:** getCoalGeneration returns 2019 generation.

3/13/2021-3/17/2021
> Debug, test, and finalize. Finished interface, cleaning up documentation, and analysis of outputs. 

4/15/2021-4/19/2021
> Added coal generation from dcorrell. Add state filtering functionality as well. Compare emission rates with EIA historical values (lookin' good). Clean up the pandas code and update readme. Remove averaging based on data given by dcorrell


## Interface

There are three functions that should be included in the public interface of this module:
1. `getCoalPlants`
2. `getPlantGeneration`
3. `getMarginalHealthCosts`. 

**All returned pandas containers are indexed by ORIS plant code. Missing data are denoted by `np.nan`.**

`getCoalPlants`: Input region(s) (`str` or `list`). Each region string should be consistent with NERC region, balancing authority codes, and state abbreviations as found in the EIA-860 dataset. Returns ORIS codes, nameplate (coal) capacities, and latitudes/longitudes of all coal plants in the regions (`pd.DataFrame`).

`getPlantGeneration`: Input ORIS codes (`int`, `np.ndarray`, or `pd.Series`). Returns 2019 annual plant generation in MWh (`pd.Series`). 

`getMarginalHealthCosts`: Input ORIS codes (`int`, `np.ndarray`, or `pd.Series`), season (`str`) --OPTIONAL. Return health damages per conventional generation ($/MWh) for given ORIS plant codes (`pd.Series`) based on seasonal EASIUR health costs. Season should be one of `Annual | Spring | Summer | Fall | Winter`, but defaults to `Annual`.

### Example:

Given the following file structure:

    Project
    |--main.py

Clone this module from your project directory:

    git clone github.com/ijbd/coalPlants.git

The updated file structure being:

    Project
    |--main.py
    |--coalPlants
        |--data
        |--__init__.py
        |--.gitignore
        |--coalPlants.py
        |--README.md
    
With this structure, `main.py` can use the functions from this module as follows:


    #### main.py ####

    from CoalPlants import CoalPlants

    # Generate Pandas DataFrame with ORIS CODE, latitude, and longitude
    plants = CoalPlants.getCoalPlants('PJM') 

    # Only include 2019 generation
    plants['2019 Generation (MWh)'] = CoalPlants.getPlantGeneration(plants['Plant Code'])

    # Marginal Health Costs
    plants['Marginal Health Cost ($/MWh)'] = CoalPlants.getMarginalHealthCosts(plants['Plant Code'])

    print(plants.head())

The output from `main.py` is:
    
    Plant Code  Latitude Longitude  Coal Capacity (MW)  2019 Generation (MWh)  Marginal Health Cost ($/MWh)
            594  38.5857  -75.2341               445.5               119120.1                     99.811392
            602    39.18  -76.5389              1370.2              2206360.7                     36.429497
            876  39.5906  -89.4964              1319.0              3109175.0                     19.296591
            879  40.5408  -89.6786              1785.6              2326413.0                     31.899453
            883  42.3833  -87.8133               681.7              1179550.0                     53.531618


## Data Sources

**Sample data is already processed in `marginalHealthCosts.csv`**, but the descriptions of each dataset, and the steps taken to get them, are outlined below.

### EASIUR:
>"The Estimating Air pollution Social Impact Using Regression (EASIUR) model is an easy-to-use tool estimating the social cost (or public health cost) of emissions in the United States. The EASIUR model was derived using regression on a large dataset created by CAMx, a state-of-the-art chemical transport model. The EASIUR closely reproduce the social costs of emissions predicted by full CAMx simulations but without the high computational costs." 

The marginal social costs provided by EASIUR are functions of population age, income, and the USD value. The data provided is for 2020 population and income, in 2010 USD. An inflation rate of 1.2 is used to estimate these costs in 2020 USD (applied in `easiur.py`, after processing)

To get EASIUR Data:
1. Run `getEasiurLocs.py` from the `data/easiur_msc` directory. This script will pull the locations of every power plant in the United States and compile them in a CSV file. It does not include generators with no latitude/longitude locations, and it fixes a latitude typo for plant #62242 in New York. This file is used in conjuction with the EASIUR Online Data Access Tool.
2. Go to the [EASIUR Online Tool](https://barney.ce.cmu.edu/~jinhyok/easiur/online/) [1,2], and use the batch conversion tool by uploading the file generated by `getEasiurLocs.py`. Each line of the output file contains a location and the corresponding Marginal Social Cost of 4 pollutants
3. Move the output file back to `data/easiur_msc`, then run the `processEasiur.py`.

### eGRID Annual Emissions
This [dataset](https://www.epa.gov/egrid/download-data) [3] provides *annual* plant-level generation and emissions (CO2, NOx, and SO2). 

### EIA-860 
>"The survey Form EIA-860 collects generator-level specific information about existing and planned generators and associated environmental equipment at electric power plants with 1 megawatt or greater of combined nameplate capacity. Summary level data can be found in the Electric Power Annual."

Available [here](https://www.eia.gov/electricity/data/eia860/) [4].

## Citations

[1] Jinhyok Heo, Peter J. Adams, H. Gao. (2016) "Reduced-form modeling of public health impacts of inorganic PM2.5 and precursor emissions", Atmospheric Environment, 137, 80—89,. doi:10.1016/j.atmosenv.2016.04.026

[2] Jinhyok Heo, Peter J. Adams, H. Gao. (2016) "Public Health Costs of Primary PM2.5 and Inorganic PM2.5 Precursor Emissions in the United States", Environmental Science & Technology, 50 (11), 6061—6070. doi:10.1021/acs.est.5b06125

[3] Environmental Protection Agency (2019) "Emissions and Generation Resource Integrated Database" 

[4] Energy Information Administration, Form EIA-930 User Guide Known Issues (2020).550
