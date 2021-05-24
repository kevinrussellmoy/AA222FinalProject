""" 
Some data cleansing for the solar PV data.
"""

#%%
import numpy as np
import pandas as pd

# 5 years of PV data
pvdata = pd.read_csv('solar_PV_15min_kWh.csv')
pv = pvdata[:8760*4]
pv.set_index(pd.date_range(start='2021-01-01 00:00', periods=35040, freq='15T'), inplace=True)
pv.drop(columns='Period Beginning (UTC -08:00)', inplace=True)
pv.columns = ['gen']
#%% Save to CSV
pv.to_csv("pv_gen.csv")
# %%
