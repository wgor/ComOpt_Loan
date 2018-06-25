from supporters import data_import, Scheduler, Agent
from usef_classes import FlexReq, FlexOffer, FlexOrder, UDIevent
import pulp
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
%matplotlib

dfx = data_import("input_file.xlsx")
ems_ts = dfx[("df_ems_01")]
ems_params = dfx["df_ems_params"].loc[1]
mp = dfx[("df_MA")].loc[:,"mp"]
fp = dfx[("df_MA")].loc[:,"fp"]

def solver(self):
    ''' Solves Device scheduling problem '''
    # prob variable
    lpmodel = pulp.LpProblem("Test",pulp.LpMinimize)
    print ("Run: {}".format("1"))

    # VARIABLES
    buy = pulp.LpVariable.dicts("buy", ems_ts.index, 0,upBound=self.params.loc["max_buy"], cat= "NonNegativeReals")
    sell = pulp.LpVariable.dicts("sell", ems_ts.index, 0,upBound=self.params.loc["max_sell"], cat= "NonNegativeReals")
    cap = pulp.LpVariable.dicts("batt_cap", ems_ts.index, lowBound=self.params.loc["thres_down"],
                            upBound=self.params.loc["thres_up"], cat= "NonNegativeReals")
    dis = pulp.LpVariable.dicts("discharged", ems_ts.index, cat= "NonNegativeReals")
    char = pulp.LpVariable.dicts("charged", ems_ts.index, cat= "NonNegativeReals")
    b_stat = pulp.LpVariable.dicts("state_buy", ems_ts.index, cat= "Binary")
    s_stat = pulp.LpVariable.dicts("state_sell", ems_ts.index, cat= "Binary")
    d_stat = pulp.LpVariable.dicts("stat_dis", ems_ts.index, cat= "Binary")
    c_stat = pulp.LpVariable.dicts("stat_char", ems_ts.index, cat= "Binary")

    ############################ OBJECTIVE ################################
    lpmodel += pulp.lpSum(buy[t]*self.ts.mp[t]-sell[t]*self.ts.fp[t] for t in ems_ts.index)

    #################### BASELINE CONSTRAINTS #############################

    for t in ems_ts.index:

    #BATTERY CONSTRAINT 1: charging or discharging in t
        con1 = pulp.LpConstraint(e=d_stat[t]+c_stat[t], rhs = 1, sense=-1)
        lpmodel.addConstraint(con1)
        #lpmodel += pulp.LpConstraint(e=d_stat[t] + c_stat[t], rhs = 1, sense=-1)
    #BATTERY CONSTRAINT 2: char and dischar limits, if stat is 1
        #con2_1 = pulp.LpConstraint(e=self.params.min_dis*d_stat[t], rhs = dis[t], sense=-1)
        lpmodel += self.params.min_dis*d_stat[t] <= dis[t]
        lpmodel += self.params.max_dis*d_stat[t] >= dis[t]
        lpmodel += self.params.min_char*c_stat[t] <= char[t]
        lpmodel += self.params.max_char*c_stat[t] >= char[t]
    #BATTERY CONSTRAINT 4: battery cap must be between low and high threshold
        con3_1 = pulp.LpConstraint(e=cap[t], rhs = self.params.thres_down, sense=1)
        lpmodel.addConstraint(con3_1)
        con3_2 = pulp.LpConstraint(e=cap[t], rhs = self.params.thres_up, sense=-1)
        lpmodel.addConstraint(con3_2)
        #lpmodel += cap[t] <= self.params.thres_up
    #BATTERY CONSTRAINT 5: Init and End State of BatteryCap
        laststep = t-1
        #ARN4_1 = pulp.LpConstraint(e=cap[min(ems_ts.index)], rhs = self.params.initSOC, sense=0)
        #lpmodel.addConstraint(ARN4_1)
        #if t > 1:
            #ARN4_3 = pulp.LpConstraint(e=cap[laststep]-dis[t]+char[t], rhs = cap[t] , sense=0)
            #lpmodel.addConstraint(ARN4_3)
        #ARN4_2 = pulp.LpConstraint(e=cap[t], rhs = self.params.endSOC, sense=0)
        #lpmodel.addConstraint(ARN4_2)
        past = t-1
        if t == min(ems_ts.index):
            lpmodel += cap[min(ems_ts.index)] == self.params.initSOC
        else:
            lpmodel += cap[t]==cap[past]-dis[t]+char[t]
        if t == max(ems_ts.index):
            lpmodel += cap[t] == self.params.endSOC
    #BALANCING CONSTRAINT: sold + pv + dis == bought + demand + char per step
        lpmodel += buy[t]+self.ts.pv[t]+dis[t] == sell[t]+self.ts.dem[t]+char[t]
    #MARKET CONSTRAINT 1: maximum buy and sell quantity per step
        lpmodel += buy[t] <= self.params.max_buy*b_stat[t]
        lpmodel += sell[t] <= self.params.max_sell*s_stat[t]
    #MARKET CONSTRAINT 2: buying and selling in same step is not possible
        lpmodel += b_stat[t] + s_stat[t] <= 1
        #print (lpmodel.constraints)

    # FLEXREQUEST Contraints
        #LpVariable.
        #lpmodel += char[5] == 5
        #lpmodel += char[6] == 0
        #lpmodel += char[7] == 0
        #lpmodel += char[8] == 0
        #print (lpmodel.constraints)
        #return lpmodel

    #LpSolverDefault.msg = 1
    lpmodel.solve()
    self.costs += pulp.value(lpmodel.objective)
    self.run_status = pulp.LpStatus[lpmodel.status]
    #pulp.writeLP("log.lp", writeSOS=1, mip=1)
    print ("Costs: {}, Model_Status: {} \n".format(round(self.costs), self.run_status))

    ## WRITE OUTPUT DATA TO AGENT's TS
    for t in ems_ts.index:
        self.ts.loc[t,"sell"] = sell[t].varValue*-1
        self.ts.loc[t,"buy"] = buy[t].varValue
        self.ts.loc[t,"cap"] = cap[t].varValue
        self.ts.loc[t,"b_stat"] = b_stat[t].varValue
        self.ts.loc[t,"s_stat"] = s_stat[t].varValue
        self.ts.loc[t,"c_stat"] = c_stat[t].varValue
        self.ts.loc[t,"d_stat"] = d_stat[t].varValue
        self.ts.loc[t,"char"] = char[t].varValue
        self.ts.loc[t,"dis"] = dis[t].varValue*-1
     ## save actual batt cap for next period
    lastcap = cap[max(ems_ts.index)].varValue
    lpmodel.writeLP("log.lp")
    return

class EMS():
    #An agent with pv, battery and demand

    def __init__(self, timeseries, params):
        self.ts = timeseries
        self.params = params
        self.costs = 0

    def step(self):
        self.optimize(milp_solver)
        #self.calc_myFlex()
        #self.write_to_EXL()
        pass

    def optimize(self):
        return solver(self)

ems = EMS(ems_ts, ems_params)
ems.params
ems.ts
ems.optimize()
