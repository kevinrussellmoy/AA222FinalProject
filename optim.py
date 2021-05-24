#%%
import numpy as np
import pandas as pd
import cvxpy as cp
import matplotlib.pyplot as plt

# Global vartiables(sizes):
PV_ARRAY_SIZE_KW = 420 # kWAC rating of the PV array

#%% Obtain aggregate load
# NOTE: Must run resi_data.py, building_data.py to obtain the following CSV files!
residf = pd.read_csv('resi_load.csv', index_col=0)
bldgdf = pd.read_csv('bldg_load.csv', index_col=0)

loaddf = pd.concat([residf, bldgdf], axis=1)

#Downscale hospital, school, market by 0.25
loaddf.hospital = loaddf.hospital * 0.25
loaddf.school = loaddf.school * 0.25
loaddf.supermarket = loaddf.supermarket * 0.25

agg_load = loaddf.sum(axis=1)

## Agg load stats:
# count    35040.000000
# mean       249.675353
# std        163.964776
# min         39.648000
# 25%         98.862156
# 50%        211.096125
# 75%        398.983500
# max        747.593000

#%% Obtain aggregate PV
# NOTE: Must run pv_data.py to obtain the following CSV file!
pvdf = pd.read_csv('pv_gen.csv', index_col=0)

# Upscale to PV array kWAC rating
pvdf = pvdf * PV_ARRAY_SIZE_KW/pvdf.gen.max()

# Agg pv stats:
# count	35040.000000
# mean	80.878783
# std	119.749443
# min	0.000000
# 25%	0.000000
# 50%	0.514689
# 75%	146.658497
# max	420.000000

#%% TODO: Rest of the fucking optimization
# x = cp.Variable()

# # An infeasible problem.
# prob = cp.Problem(cp.Minimize(x), [x >= 1, x <= 0])
# prob.solve()
# print("status:", prob.status)
# print("optimal value", prob.value)
# %%
