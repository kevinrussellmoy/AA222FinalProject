# %%
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt

# Global vartiables(sizes):
PV_ARRAY_SIZE_KW = 420   # kWAC rating of the PV array
DIESEL_GEN_SIZE_KW = 1000   # kWAC rating of the diesel generator
# Diesel fuel consumption coefficients from https://ieeexplore.ieee.org/document/8494571
DIESEL_FUEL_CONS_A =   0.246 # Liters per kWh
DIESEL_FUEL_CONS_B =   0.08415 # Liters per kW (rating)

ESS_EFF_DISCHG = 0.95 # Efficiency of discharging ESS
ESS_EFF_CHG = 0.95 # Efficiency of charging ESS
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

#%% 
''' ~.~.~.~ optimization time ~.~.~.~ '''
# TODO: randomly (or not so randomly) select 7-day intervals to optimize the dispatch
# first do for a set ESS size (500 kW, 950 kWh as in BLR Microgrid)

# then make the ESS size a part of the function!
# Constrain storage size to [min, max] and similarly power
# Then find the optimum, and then find the closest "round" value and present those power flows

# then add in degradation penalty

load = agg_load.to_numpy()
pv = pvdf.to_numpy()

week1 = 4*24*7

# Try a different week in the year??

ld_wk1 = load[:week1]
pv_wk1 = pv[:week1]

# Fraction of the hour
h = 15/60

# Create a new model
m = gp.Model('microgrid')

# Create variables for:

# ESS nominal energy and power
# Assume a four-hour system
# E_nom = 1500 # kWh
# P_nom = 500 # kW
P_nom = m.addMVar(1, lb=200, ub=1000, vtype=GRB.CONTINUOUS, name='P_nom')
E_nom = m.addMVar(1, vtype=GRB.CONTINUOUS, name='E_nom')

# each power flow
# format: to_from
pv_ess = m.addMVar(week1, lb=0, ub=PV_ARRAY_SIZE_KW, vtype=GRB.CONTINUOUS, name='pv_ess')
pv_load = m.addMVar(week1, lb=0, ub=PV_ARRAY_SIZE_KW, vtype=GRB.CONTINUOUS, name='pv_load')
pv_curtail = m.addMVar(week1, lb=0, ub=PV_ARRAY_SIZE_KW, vtype=GRB.CONTINUOUS, name='pv_curtail')
ess_load = m.addMVar(week1, lb=0, vtype=GRB.CONTINUOUS, name='ess_load')
dg_ess = m.addMVar(week1, lb=0, vtype=GRB.CONTINUOUS, name='dg_ess')
dg_load = m.addMVar(week1, lb=0, vtype=GRB.CONTINUOUS, name='dg_load')
load_curtail = m.addMVar(week1, lb=0, vtype=GRB.CONTINUOUS, name='load_curtail')

ess_c = m.addMVar(week1, lb=0, vtype=GRB.CONTINUOUS, name='ess_c')
ess_d = m.addMVar(week1, lb=0, vtype=GRB.CONTINUOUS, name='ess_d')

dg = m.addMVar(week1, lb=0, vtype=GRB.CONTINUOUS, name='dg')

E = m.addMVar(week1, lb=0, vtype=GRB.CONTINUOUS, name='E')

# Decision variable to discharge (1) or charge (0)

dischg = m.addVars(week1, vtype=GRB.BINARY, name='dischg')

m.addConstr(E[0] == E_nom)
m.addConstr(E[week1-1] == 0.5*E_nom)

m.addConstr(E_nom == 4*P_nom)

for t in range(week1):
    # Power flow constraints
    m.addConstr(pv_wk1[t] == pv_ess[t] + pv_load[t] + pv_curtail[t])
    m.addConstr(ld_wk1[t] == ess_load[t] + pv_load[t] + load_curtail[t] + dg_load[t])
    m.addConstr(dg[t] == dg_load[t])
    # m.addConstr(ess_c[t] == pv_ess[t])
    m.addConstr(ess_c[t] == pv_ess[t]) # uncomment to allow ESS to charge off of DG
    m.addConstr(ess_d[t] == ess_load[t])

    # ESS power constraints
    m.addConstr(ess_c[t] <= P_nom)
    m.addConstr(ess_d[t] <= P_nom)
    # m.addConstr(ess_c[t]*ess_d[t] == 0)
    # Prevent underdischarging from overdischarging

    # Time evolution of stored energy
    if t > 0:
        # m.addConstr(E[t] == h*((1-dischg[t])*ess_c[t-1] - dischg[t]*ess_d[t-1]) + E[t-1])
        m.addConstr(E[t] == h*(ESS_EFF_CHG*ess_c[t-1] - ESS_EFF_DISCHG*ess_d[t-1]) + E[t-1])

    # Cost of fuel

#Ensure non-simultaneous charge and discharge aka why I downloaded Gurobi
m.addConstrs(0 == ess_d[i] @ ess_c[i] for i in range(week1))

# TODO: Turn this into an explicit multi-objective problem via setObjectiveN
m.setObjective(h*DIESEL_FUEL_CONS_A*dg.sum() + load_curtail.sum() + 100*P_nom, GRB.MINIMIZE)
# m.setObjective(load_curtail.sum(), GRB.MINIMIZE)


#%% Solve the optimization
m.optimize()

# #%% Get objective final value
# m.getObjective().getValue()

#%% Plot data!
xvals = np.linspace(0,7,week1) 
#%% ESS power flow
plt.plot(xvals, -ess_c.getAttr('x'))
plt.plot(xvals, ess_d.getAttr('x'))
plt.legend(['Charge', 'Discharge'], bbox_to_anchor=(1.35, 0.6))
plt.xlabel('Time')
plt.ylabel('Power (kW)')
plt.grid()
plt.title('ESS Power (Discharge positive)')
plt.figure(figsize=(10,10))

#%% DG power flow
plt.plot(xvals, dg_ess.getAttr('x'))
plt.plot(xvals, dg_load.getAttr('x'))
plt.legend(['ESS', 'Load'], bbox_to_anchor=(1.35, 0.6))
plt.xlabel('Time')
plt.ylabel('Power (kW)')
plt.grid()
plt.title('Diesel Power by End User')
plt.figure(figsize=(10,10))

#%% PV power flow
plt.plot(xvals, pv_load.getAttr('x'))
plt.plot(xvals, pv_ess.getAttr('x'))
plt.plot(xvals, pv_curtail.getAttr('x'))
plt.legend(['Load', 'ESS', 'Curtailed'], bbox_to_anchor=(1.35, 0.6))
plt.xlabel('Time')
plt.ylabel('Power (kW)')
plt.grid()
plt.title('PV Power by End User')
plt.figure(figsize=(10,10))
#%% Load power flow

plt.plot(xvals, dg_load.getAttr('x'))
plt.plot(xvals, pv_load.getAttr('x'))
plt.plot(xvals, ess_load.getAttr('x'))
plt.legend(['Diesel', 'PV', 'ESS'], bbox_to_anchor=(1.35, 0.6))
plt.xlabel('Time')
plt.ylabel('Power (kW)')
plt.grid()
plt.title('Load Power by Source')
plt.figure(figsize=(10,10))

# %% plot all relevant quantities on one plot!
plt.plot(xvals, dg.getAttr('x'))
plt.plot(xvals, pv_wk1)
plt.plot(xvals, ess_d.getAttr('x') - ess_c.getAttr('x'))
plt.plot(xvals, ld_wk1)
plt.legend(['Diesel', 'PV', 'ESS', 'Load'], bbox_to_anchor=(1.35, 0.6))
plt.xlabel('Time')
plt.ylabel('Power (kW)')
plt.grid()
plt.title('Power Flow Summary')
plt.figure(figsize=(10,10))
# %%
plt.plot(xvals , E.getAttr('x'))

# %%
plt.plot(xvals, load_curtail.getAttr('x'))
# %%
