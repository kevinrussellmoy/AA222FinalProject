#%%
import numpy as np
import pandas as pd
import cvxpy as cvx
import matplotlib.pyplot as plt

# Global vartiables(sizes):
PV_ARRAY_SIZE_KW = 420 # kWAC rating of the PV array
DIESEL_GEN_SIZE_KW = 1000 # kWAC rating of the diesel generator
# Diesel fuel consumption coefficients from https://ieeexplore.ieee.org/document/8494571
DIESEL_FUEL_CONS_A = 0.246 # Liters per kWh
DIESEL_FUEL_CONS_B = 0.08415 # Liters per kW (rating)

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

# randomly (or not so randomly) select 7-day intervals to optimize the dispatch
# first do for a set ESS size (500 kW, 950 kWh as in BLR Microgrid)

# then make the ESS size a part of the function!

# then add in degradation penalty

load = agg_load.to_numpy()
pv = pvdf.to_numpy()

week1 = 4*24*7

ld_wk1 = load[:week1]
pv_wk1 = pv[:week1]

# Create variables for:

# each power flow
# format: to_from
pv_ess = cvx.Variable(week1)
pv_load = cvx.Variable(week1)
pv_curtail = cvx.Variable(week1)
ess_load = cvx.Variable(week1)
dg_ess = cvx.Variable(week1)
dg_load = cvx.Variable(week1)
load_curtail = cvx.Variable(week1)

# ESS charge and discharge
ess_C = cvx.Variable(week1)
ess_D = cvx.Variable(week1)

# Total ESS dispatch (positive discharge, negative charge)
ess_disp = cvx.Variable(week1)

# Total diesel genset power production
dg = cvx.Variable(week1)

# energy stored in the ESS
E = cvx.Variable(week1)
# nominal energy and power
E_nom = 2000 # kWh
P_nom = 500 # kW

# Fraction of the hour
h = 15/60

# Initialize cost, constraint forms
cost = []
constraints = []

constraints.append(E[0] == E_nom) # assume start with full ESS
constraints.append(E[week1-1] == 0.5*E_nom) # assume end half-charged

#####
##### TODO: Convert power into -P_nom <= P[t] <= P_nom
#####       with discharging as max(P[t], 0) and charging as -min(P[t], 0)

for t in range(week1):
    # Power flow constraints
    constraints.append(pv_wk1[t] == pv_ess[t] + pv_load[t] + pv_curtail[t])
    constraints.append(ld_wk1[t] == ess_load[t] + pv_load[t] + dg_load[t])
    # constraints.append(dg[t] == dg_load[t])
    constraints.append(dg[t] == dg_ess[t] + dg_load[t])
    constraints.append(ess_C[t] == pv_ess[t])
    constraints.append(ess_D[t] == ess_load[t])
    constraints.append(ess_disp[t] == ess_D[t] - ess_C[t])

    # Prevent underdischarging from overdischarging
    constraints.append(E[t] >= h * ess_D[t])

    # Time evolution of stored energy
    if t > 0:
        constraints.append(E[t] == E[t-1] + h*(ess_C[t-1] - ess_D[t-1]))

    # Cost of fuel
    cost.append(h*dg[t]*DIESEL_FUEL_CONS_A + DIESEL_GEN_SIZE_KW * DIESEL_FUEL_CONS_B)

# Stored energy constraints
constraints.append(E <= E_nom)
constraints.append(E >= 0)


# ESS power constraints
constraints.append(ess_D <= P_nom)
constraints.append(ess_D >= 0)
constraints.append(ess_C <= P_nom)
constraints.append(ess_C >= 0)

# DG, PV, load power constraints
constraints.append(dg_ess >= 0)
constraints.append(dg_load >= 0)
constraints.append(pv_curtail >= 0)
constraints.append(pv_ess >= 0)
constraints.append(pv_load >= 0)
constraints.append(ess_load >= 0)

#%%
objective = cvx.Minimize(cvx.sum(cost))
prob = cvx.Problem(objective, constraints)
prob.solve()

# %% plot all relevant quantities on one plot!
plt.plot(dg.value)
plt.plot(pv_wk1)
plt.plot(ld_wk1)
plt.plot(ess_D.value - ess_C.value)

#%%
plt.plot(ess_D.value)
plt.plot(ess_C.value)


# %% Examples

# x = cp.Variable()

# # An infeasible problem.
# prob = cp.Problem(cp.Minimize(x), [x >= 1, x <= 0])
# prob.solve()
# print("status:", prob.status)
# print("optimal value", prob.value)
# # %% Implement one step of MPC using cvxpy
# # Input: x(t), A, B, Q, R, P, N, x_bar, u_bar, x0, X_f
# # Output: u(t)

# def opt_finite_traj(A, B, Q, R, P, N, x_bar, u_bar, x0, X_f0=False):
#     converged = False
#     n = Q.shape[0] # state dimension
#     m = R.shape[0] # control dimension  
#     # Initialize variables
#     x = cvx.Variable((N+1, n))
#     u = cvx.Variable((N, m))
#     # Initialize cost, constraint forms
#     cost = []
#     cost.append(cvx.quad_form(x[N],P))
#     constraints = []
#     constraints.append(x[0] == x0)
#     for k in range(N):
#         cost.append(cvx.quad_form(x[k], Q))
#         cost.append(cvx.quad_form(u[k], R))
#         constraints.append(x[k+1] == (A @ (x[k])  + B @ (u[k])))
#     constraints.append(u <= u_bar)
#     constraints.append(u >= -u_bar)
#     constraints.append(x <= x_bar)
#     constraints.append(x >= -x_bar)
#     if X_f0:
#         constraints.append(x[N] == np.array([0, 0]))
#     objective = cvx.Minimize(cvx.sum(cost))
#     prob = cvx.Problem(objective, constraints)
#     prob.solve()
#     u_new = u.value
#     if prob.status == cvx.OPTIMAL:
#         converged = True
#     # Note this is either -Inf or Inf if infeasible or unbounded
#     return converged, u_new

# %%
