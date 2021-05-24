""" 
Some data cleansing for the residential data.
"""
#%%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from copy import deepcopy
my_path = os.path.dirname(os.path.realpath(__file__))

#%% Load in data

metadata= pd.read_csv("15minute_data_california/metadata.csv", date_parser=pd.to_datetime)

loaddata = pd.read_csv("15minute_data_california/15minute_data_california.csv")
loaddata = loaddata[['dataid', 'local_15min', 'grid']]
# %% Filter for potential residential loads to use
# Drop description row
resi_md = metadata.drop(metadata.index[0])

# convert eGauge 1-minute data into datetime
resi_md.egauge_1min_max_time = pd.to_datetime(resi_md.egauge_1min_max_time)
resi_md.egauge_1min_min_time = pd.to_datetime(resi_md.egauge_1min_min_time)
#%%
# Filter out only california, without solar, with grid eGauge data greater than one year:
resi_md = resi_md.loc[(resi_md.state == 'California') & (resi_md.grid == 'yes') & \
    (resi_md.solar != 'yes') & (resi_md.egauge_1min_data_availability.str.strip('%').astype('float') == 100) & \
    ((resi_md.egauge_1min_max_time - resi_md.egauge_1min_min_time).dt.days >= 365)]

#%% Extract array of dataids for load data
ids = resi_md.dataid.astype('int').to_numpy()
# %%
ld = loaddata[loaddata['dataid'].isin(ids)]
ld_ids = ld.dataid.unique()
# ld.local_15min = pd.to_datetime(ld.local_15min)
# # ld.local_15min = pd.to_datetime(ld.local_15min)
# ld = ld.set_index(['dataid', 'local_15min'])
#%%

resi_load = pd.DataFrame(index=pd.date_range(start='2021-01-01 00:00', periods=35040, freq='15T'))

#%% Compile load data as 15-minute data for one year

for loadid in ids:
    if loadid in ld_ids:
        coln = 'load' + str(loadid)
        print(coln)

        ld1 = ld.loc[(ld.dataid == loadid)]
        ld1.drop('dataid', axis=1, inplace=True)
        ld1['local_15min'] = ld1['local_15min'].astype(str).str[:-6]
        ld1['local_15min'] = pd.to_datetime(ld1['local_15min'])
        ld1.reset_index(inplace=True, drop=True)
        first = ld1.local_15min[0]

        rs = pd.date_range(start=first, periods=35040, freq='15T')

        ld1.set_index('local_15min', inplace=True)
        ld1 = ld1.reindex(rs, method='pad')

        ld1.reset_index(inplace=True)
        ld1['index'] = ld1['index'].apply(lambda x: x.strftime('%m-%d %H:%M'))
        ld1.set_index('index', inplace=True)

        ld1_sorted = ld1.sort_index()
        ld1_sorted.set_index(pd.date_range(start='2021-01-01 00:00', periods=35040, freq='15T'), inplace=True)
        # plt.plot(ld1_sorted.grid)
        # plt.show()

        resi_load[coln] = ld1_sorted.grid

#%% Save to CSV
resi_load.to_csv("resi_load.csv")
#%% 
