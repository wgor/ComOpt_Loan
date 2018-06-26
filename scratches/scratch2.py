from utils import data_import
import pulp
import pandas as pd
# %matplotlib

dfx = data_import("input_file.xlsx")
ems_ts = dfx[("df_ems_01")]
ems_params = dfx["df_ems_params"].loc[1]
req_up = dfx[("df_MA")].loc[:,"req_up"]
req_down = dfx[("df_MA")].loc[:,"req_down"]
flex_switch = dfx[("df_MA")].loc[:,"flex_switch"]

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
    buy_switch = pulp.LpVariable.dicts("state_buy", ems_ts.index, cat= "Binary")
    sell_switch = pulp.LpVariable.dicts("state_sell", ems_ts.index, cat= "Binary")
    dis_switch = pulp.LpVariable.dicts("stat_dis", ems_ts.index, cat= "Binary")
    char_switch = pulp.LpVariable.dicts("stat_char", ems_ts.index, cat= "Binary")


    ############################ OBJECTIVE ################################
    lpmodel += pulp.lpSum(buy[t]*self.ts.mp[t]-sell[t]*self.ts.fp[t] for t in ems_ts.index)

    #################### BASELINE CONSTRAINTS #############################

    for t in ems_ts.index:

    #BATTERY CONSTRAINT 1: charging or discharging in t
        lpmodel += dis_switch[t] + char_switch[t] <= 1
    #BATTERY CONSTRAINT 2: char and dischar limits, if stat is 1
        lpmodel += self.params.min_dis*dis_switch[t] <= dis[t]
        lpmodel += self.params.max_dis*dis_switch[t] >= dis[t]
        lpmodel += self.params.min_char*char_switch[t] <= char[t]
        lpmodel += self.params.max_char*char_switch[t] >= char[t]
    #BATTERY CONSTRAINT 4: battery cap must be between low and high threshold
        lpmodel += cap[t] >= self.params.thres_down
        lpmodel += cap[t] <= self.params.thres_up
    #BATTERY CONSTRAINT 5: Init and End State of BatteryCap
        past = t-1
        if t == min(ems_ts.index):
           lpmodel += cap[min(ems_ts.index)] == self.params.initSOC
        else:
           lpmodel += cap[t]==cap[past]-dis[t]+char[t]
        if t == max(ems_ts.index):
           lpmodel += cap[t] == self.params.endSOC
    #BALANCING CONSTRAINT: buy + pv + dis + req_up == bought + demand + char per step
        lpmodel += buy[t]+self.ts.pv[t]+dis[t] == sell[t]+self.ts.dem[t]+char[t]
    #MARKET CONSTRAINT 1: maximum buy and sell quantity per step
        lpmodel += buy[t] <= self.params.max_buy*buy_switch[t]
        lpmodel += sell[t] <= self.params.max_sell*sell_switch[t]
    #MARKET CONSTRAINT 2: buying and selling in same step is not possible
        lpmodel += buy_switch[t] + sell_switch[t] <= 1
        #print (lpmodel.constraints)

    # FLEXREQUEST Contraints
        if flex_req[t] > 0 :
            lpmodel += char[t] == flex_req[t][t]
        elif flex_req[t] > -1 :
            lpmodel += dis[t] == flex_req[t][t]
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
    print ("Costs: {}, Model_Status: {} \n".format(round(self.costs), self.run_status))

    ## WRITE OUTPUT DATA TO AGENT's TS
    for t in ems_ts.index:
        self.ts.loc[t,"sell"] = sell[t].varValue*-1
        self.ts.loc[t,"buy"] = buy[t].varValue
        self.ts.loc[t,"cap"] = cap[t].varValue
        self.ts.loc[t,"buy_switch"] = buy_switch[t].varValue
        self.ts.loc[t,"sell_switch"] = sell_switch[t].varValue
        self.ts.loc[t,"char_switch"] = char_switch[t].varValue
        self.ts.loc[t,"dis_switch"] = dis_switch[t].varValue
        self.ts.loc[t,"char"] = char[t].varValue
        self.ts.loc[t,"dis"] = dis[t].varValue*-1

     ## save actual batt cap for next period
    lastcap = cap[max(ems_ts.index)].varValue
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

writer = pd.ExcelWriter('input_file.xlsx')
ems.ts.to_excel(writer,'output')

#plt.plot(ems.ts.loc[:,"char_switch"])
#plt.show()
