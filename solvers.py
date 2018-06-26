from utils import data_export
from pulp import *


def milp_solver(agents_list:"list",type:"solo/coop", flex_req:"array"):
      # prob variable
      # if flex_req != None:
      #     print ("Flex_Request: {}".format(str(flex_req)))
      # elif flex_req == None:
      #     print ("No Flex Req")
      costs = 0
      run_status = 0
      lpmodel = pulp.LpProblem("Test",pulp.LpMinimize)
      # if type == "base":
      #     print ("Run:Baseline - EMS:{}".format(ems.agent_id))
      # elif type == "req_01":
      #     print ("Run:Request_01 - EMS:{}".format(ems.agent_id))
      for ems in agents_list:
          # VARIABLES
          buy = pulp.LpVariable.dicts("buy", ems.ts.index, 0,upBound=ems.params.loc["max_buy"], cat= "NonNegativeReals")
          sell = pulp.LpVariable.dicts("sell", ems.ts.index, 0,upBound=ems.params.loc["max_sell"], cat= "NonNegativeReals")
          cap = pulp.LpVariable.dicts("batt_cap", ems.ts.index, lowBound=ems.params.loc["thres_down"],
                                  upBound=ems.params.loc["thres_up"], cat= "NonNegativeReals")
          dis = pulp.LpVariable.dicts("discharged", ems.ts.index, cat= "NonNegativeReals")
          char = pulp.LpVariable.dicts("charged", ems.ts.index, cat= "NonNegativeReals")
          buy_switch = pulp.LpVariable.dicts("state_buy", ems.ts.index, cat= "Binary")
          sell_switch = pulp.LpVariable.dicts("state_sell", ems.ts.index, cat= "Binary")
          dis_switch = pulp.LpVariable.dicts("stat_dis", ems.ts.index, cat= "Binary")
          char_switch = pulp.LpVariable.dicts("stat_char", ems.ts.index, cat= "Binary")

          ############################ OBJECTIVE ################################
          lpmodel += pulp.lpSum(buy[ems][t]*ems.ts.mp[ems][t]-sell[ems][t]*ems.ts.fp[ems][t] for ems,t in (agent_list,ems.ts.index)
          #################### BASELINE CONSTRAINTS #############################

          for t in ems.ts.index:
              for ems in agents_list:
              #BATTERY CONSTRAINT 1: charging or discharging in t
                  lpmodel += dis_switch[t] + char_switch[t] <= 1
              #BATTERY CONSTRAINT 2: char and dischar limits, if stat is 1
                  lpmodel += ems.params.min_dis*dis_switch[t] <= dis[t]
                  lpmodel += ems.params.max_dis*dis_switch[t] >= dis[t]
                  lpmodel += ems.params.min_cha*char_switch[t] <= char[t]
                  lpmodel += ems.params.max_cha*char_switch[t] >= char[t]
              #BATTERY CONSTRAINT 4: battery cap must be between low and high threshold
                  lpmodel += cap[t] >= ems.params.thres_down
                  lpmodel += cap[t] <= ems.params.thres_up
              #BATTERY CONSTRAINT 5: Init and End State of BatteryCap
                  past = t-1
                  if t == min(ems.ts.index):
                     lpmodel += cap[min(ems.ts.index)] == ems.params.initSOC
                  else:
                     lpmodel += cap[t]==cap[past]-dis[t]+char[t]
                  if t == max(ems.ts.index):
                     lpmodel += cap[t] == ems.params.endSOC
              #BALANCING CONSTRAINT: buy + gen + dis + req_up == bought + demand + char per step
                  lpmodel += buy[t]+ems.ts.gen[t]+dis[t] == sell[t]+ems.ts.dem[t]+char[t]
              #MARKET CONSTRAINT 1: maximum buy and sell quantity per step
                  lpmodel += buy[t] <= ems.params.max_buy*buy_switch[t]
                  lpmodel += sell[t] <= ems.params.max_sell*sell_switch[t]
              #MARKET CONSTRAINT 2: buying and selling in same step is not possible
                  lpmodel += buy_switch[t] + sell_switch[t] <= 1
                  #print (lpmodel.constraints)

              # # FLEXREQUEST Contraints
                  # if type == "req_01":
                  #     if flex_req.values["up"].loc[t] != 0 :
                  #         lpmodel += char[t] == flex_req.values["up"].loc[t]
                  #     elif flex_req.values["down"].loc[t] != 0:
                  #         lpmodel += dis[t] == flex_req.values["down"].loc[t]

              #LpSolverDefault.msg = 1
              lpmodel.solve()
              costs += pulp.value(lpmodel.objective)
              run_status = pulp.LpStatus[lpmodel.status]
              #print ("Costs: {}, Model_Status: {} \n".format(round(costs), run_status))

              ## WRITE OUTPUT DATA TO AGENT's TS
              for t in ems.ts.index:
                  ems.ts.loc[t,"sell"] = sell[t].varValue*-1
                  ems.ts.loc[t,"buy"] = buy[t].varValue
                  ems.ts.loc[t,"cap"] = cap[t].varValue
                  ems.ts.loc[t,"buy_switch"] = buy_switch[t].varValue
                  ems.ts.loc[t,"sell_switch"] = sell_switch[t].varValue
                  ems.ts.loc[t,"char_switch"] = char_switch[t].varValue
                  ems.ts.loc[t,"dis_switch"] = dis_switch[t].varValue
                  ems.ts.loc[t,"char"] = char[t].varValue
                  ems.ts.loc[t,"dis"] = dis[t].varValue*-1
                  ems.ts.loc[t, "batt_flex_up"] = ems.params.loc["thres_up"]-cap[t].varValue
                  ems.ts.loc[t, "batt_flex_down"] = cap[t].varValue-ems.params.loc["thres_down"]
               ## save actual batt cap for next period
              #lastcap = cap[max(ems.ts.index)].varValue
              data_export("ComOpt.xlsm", ems, costs, run_status)
              return ems.ts, costs
