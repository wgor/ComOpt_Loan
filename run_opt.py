% load_ext autoreload
% autoreload 2

from supporters import data_import, data_export, Agent
from model import Environment, EMS, TradingAgent
from messages import Prognosis, FlexReq, FlexOffer, FlexOrder, UDIevent
#from solvers import milp_solver
from pulp import *
import random
import datetime as dt
import xlwings as xw
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

################ TEST MILP SOLVER #######################
# %%
inputs = data_import("ComOpt.xlsm")
if __name__ == '__main__':
    env = Environment(data=inputs)
    env.step()
# %%


import sys
sys.path.append('D:/CWI/ComOPT/ComOPT_model/ComOpt')

import sys
print(sys.path)















df = pd.DataFrame()
df1 = env.EMS[0].ts
df2 = env.EMS[1].ts
inputs["ems_ts"][]
lists = []
times = []
ems = ["a01","a02","a03"]
for time in df1.index:
    times.append(time)

lists.append(times)
lists.append(ems)

ind = pd.MultiIndex.from_product(lists, names=['time', 'ems'])
df = pd.DataFrame(df1, index=ind)

for col in env.EMS[0].ts.columns:
    for ems in enumerate(env.EMS):
        #print("switch")
        for t in times:
            print ("now")
            df.at[(t, ems[1].agent_id),col] = ems[1].ts.loc[t,col]

df
    #for t,val in zip(times, env.EMS[e[0]].ts.loc[:,"dem"]):
        #df.at[(t, ems),"dem"] = val
df



buy_sum_df, buy_costs_df  = pd.DataFrame(df1)
buy_sum_df
