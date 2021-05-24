""" 
Some data cleansing for the building data.
"""

#%%
import numpy as np
import pandas as pd

hospdata = pd.read_csv("Reference-Hospital.csv", names=['load'], header=0)
hospdata.set_index(pd.date_range(start='2021-01-01 00:00', periods=8760, freq='H'), inplace=True)
rs = pd.date_range(start='2021-01-01 00:00', periods=35040, freq='15T')
hospdata = hospdata.reindex(rs)
hospdata.load.interpolate(inplace=True)

schooldata = pd.read_csv("Reference-Secondary School.csv", names=['load'], header=0)
schooldata.set_index(pd.date_range(start='2021-01-01 00:00', periods=8760, freq='H'), inplace=True)
rs = pd.date_range(start='2021-01-01 00:00', periods=35040, freq='15T')
schooldata = schooldata.reindex(rs)
schooldata.load.interpolate(inplace=True)

marketdata = pd.read_csv("Reference-Supermarket.csv", names=['load'], header=0)
marketdata.set_index(pd.date_range(start='2021-01-01 00:00', periods=8760, freq='H'), inplace=True)
rs = pd.date_range(start='2021-01-01 00:00', periods=35040, freq='15T')
marketdata = marketdata.reindex(rs)
marketdata.load.interpolate(inplace=True)

# %%
bldg_load = pd.DataFrame(index=pd.date_range(start='2021-01-01 00:00', periods=35040, freq='15T'))

bldg_load['hospital'] = hospdata.load
bldg_load['school'] = schooldata.load
bldg_load['supermarket'] = marketdata.load

#%% Save to CSV
bldg_load.to_csv("bldg_load.csv")
# %%
