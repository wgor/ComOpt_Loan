import pandas as pd
import xlwings as xw
import copy
import pulp

def solver(name,
           multi_ix_df,
           parameter,
           flex_request,
           flags,
           timeperiods,
           type,
           mode,
           active_ems, base_net):
    """Please fill this out and explain function parameters."""
    # Solver needs demand and generation and parameters and flex_request
    timeseries = pd.DataFrame(multi_ix_df)
    parameter = pd.DataFrame(parameter)

    battery_flexibility = "No"
    DSM_flexibility = "No"
    curtailment_flexibility = "No"
    internal_balance = "No"
    print (name)
    request_pos = pd.Series(0,index=timeperiods).astype("float64")
    request_neg = pd.Series(0,index=timeperiods).astype("float64")

    try:
        flags.loc["Batteries", "EMS"]
        print(flags.loc["Batteries", "EMS"])
        battery_flexibility = "Yes"
    except:
        print("No Battery Flexibility")
        if battery_flexibility == "No":
            parameter.loc["Threshold-Down",:] = 0
            parameter.loc["Threshold-Up",:] = 0
            parameter.loc["Battery-SOC-Init"] = 0
            parameter.loc["Battery-SOC-End"] = 0
        pass

    try:
        flags.loc["DSM", "EMS"]
        DSM_flexibility = "Yes"
    except:
        pass

    try:
        flags.loc["Curtailment", "EMS"]
        curtailment_flexibility = "Yes"
    except:
        pass

    if type == "REQ":
        for val,time in zip(flex_request.values, timeperiods):
            if val > 0:
                request_pos[time] = val
            if val < 0:
                request_neg[time] = val*-1

    costs = 0
    milp = pulp.LpProblem("Cost minimising scheduling problem", pulp.LpMinimize)
    #data dat gets passed in

    ############################ VARIABLES ################################

    buy = pulp.LpVariable.dicts("buy",((time, ems) for time, ems in timeseries.index),
                                lowBound=0,
                                cat="NonNegativeReals")
    sell = pulp.LpVariable.dicts("sell",((time, ems) for time, ems in timeseries.index),
                                lowBound=0,
                                cat="NonNegativeReals")
    cap = pulp.LpVariable.dicts("cap",((time, ems) for time, ems in timeseries.index),
                                cat="NonNegativeReals")
    dis = pulp.LpVariable.dicts("dis",((time, ems) for time, ems in timeseries.index),
                                cat="NonNegativeReals")
    char = pulp.LpVariable.dicts("char",((time, ems) for time, ems in timeseries.index),
                                cat="NonNegativeReals")
    # flex_neg = pulp.LpVariable.dicts("flex_neg",((time, ems) for time, ems in timeseries.index),
    #                             lowBound=0,
    #                             cat="NonNegativeReals")
    # flex_pos = pulp.LpVariable.dicts("flex_pos",((time, ems) for time, ems in timeseries.index),
    #                             lowBound=0,
    #                             cat="NonNegativeReals")
    buy_switch = pulp.LpVariable.dicts("buy_switch",((time, ems) for time, ems in timeseries.index),
                                cat="Binary")
    sell_switch = pulp.LpVariable.dicts("sell_switch",((time, ems) for time, ems in timeseries.index),
                                cat="Binary")
    dis_switch = pulp.LpVariable.dicts("dis_switch",((time, ems) for time, ems in timeseries.index),
                                cat="Binary")
    char_switch = pulp.LpVariable.dicts("char_switch",((time, ems) for time, ems in timeseries.index),
                                cat="Binary")
    # batt_active = pulp.LpVariable.dicts("batt_active",((time, ems) for time, ems in timeseries.index),
    #                             cat="Binary")
    # batt_switched_on = pulp.LpVariable.dicts("batt_switched_on",((time, ems) for time, ems in timeseries.index),
                                #cat="Binary")
    # flex_pos_active = pulp.LpVariable.dicts("flex_pos_active",((time, ems) for time, ems in timeseries.index),
    #                             cat="Binary")
    # flex_neg_active = pulp.LpVariable.dicts("flex_neg_active",((time, ems) for time, ems in timeseries.index),
    #                             cat="Binary")

    ############################ OBJECTIVE ################################
    if type == "BASE":
        milp += pulp.lpSum([buy[(time,ems)] * timeseries["mp"][time][ems] - sell[(time,ems)] * timeseries["fit"][time][ems]
                            #+ batt_switched_on[(time,ems)] * parameter[ems]["Start-Up-Costs"]
                            for time, ems in timeseries.index])

    if type == "REQ":
        milp += pulp.lpSum([ (request_pos[time]-char[(time, ems)])
                            + (request_neg[time]-dis[(time, ems)])
                            for time, ems in timeseries.index])

    #################### BASELINE CONSTRAINTS #############################
    for time, ems in timeseries.index:
        ''' access LpVariable: e.g. buy[time,ems]
            access data from "outside": e.g timeseries["gen"][time][ems]'''

        # 1.CONSTRAINT Storage: Either charging or discharging in every timestep
        milp += dis_switch[(time, ems)] + char_switch[(time, ems)] <= 1

        # 2.CONSTRAINT Storage: Min/Max charging rates and Min/Max discharging rates [in kW]
        milp += parameter[ems]["Discharge-Min"]*dis_switch[(time, ems)] <= dis[(time,ems)]
        milp += parameter[ems]["Discharge-Max"]*dis_switch[(time, ems)] >= dis[(time,ems)]
        milp += parameter[ems]["Charge-Min"]*char_switch[(time, ems)] <= char[(time,ems)]
        milp += parameter[ems]["Charge-Max"]*char_switch[(time, ems)] >= char[(time,ems)]

        # 3.CONSTRAINT Storage: Storage capacity must be between low and high thresholds in every timestep.
        milp += cap[(time, ems)] >= parameter[ems]["Threshold-Down"] #parameter[ems]["Threshold-Down"]
        milp += cap[(time, ems)] <= parameter[ems]["Threshold-Up"] #parameter[ems]["Threshold-Up"]

        # 4.CONSTRAINT Storage: Init and End State of Battery Cap constraints, capacity at every step.
        if time == 1:
            milp += cap[(1,ems)] == parameter[ems]["Battery-SOC-Init"]
            milp += dis[1,ems] == 0
            milp += dis_switch[(1, ems)] == 0
            milp += char[1,ems] == 0
            milp += char_switch[(1, ems)] == 0
        else:
            milp += cap[(time, ems)] == cap[(time-1, ems)]-dis[(time, ems)]+char[(time, ems)]
        if time == 24:
            #if parameter.loc["init_eq_end_switch", ems] == 1:
            milp += cap[(24,ems)] == parameter[ems]["Battery-SOC-End"]
            milp += dis[24,ems] == 0
            milp += dis_switch[(24, ems)] == 0
            milp += char[24,ems] == 0
            milp += char_switch[(24, ems)] == 0

        #5. CONSTRAINT MARKET : Maximum buy and sell quantity per step

        ## 6. CONSTRAINTS Flex-Requests :
        #if mode == "flex-split":
             # milp += flex_pos[(time, ems)] == request_pos[time] * flex_pos_active[(time, ems)]
             # milp += flex_neg[(time, ems)] == request_neg[time] * flex_neg_active[(time, ems)]
             # milp += flex_pos[(time, ems)] >= 0
             # milp += flex_neg[(time, ems)] <= 0
             # milp += flex_pos_active[(time,ems)] + flex_neg_active[(time,ems)] <= 1

        #7. BALANCING CONSTRAINT: buy + gen + dis + req_up == bought + demand + char per step
        if type == "BASE":
            milp += buy[(time,ems)] + timeseries["gen"][time][ems] + dis[(time,ems)] + request_neg[time] == sell[(time,ems)] + timeseries["dem"][time][ems] + char[(time,ems)] + request_pos[time]
            milp += buy_switch[(time,ems)] + sell_switch[(time,ems)] <= 1
            milp += buy[(time, ems)] <= parameter[ems]["Buying-Max"]*buy_switch[(time, ems)]
            milp += sell[(time, ems)] <= parameter[ems]["Selling-Max"]*sell_switch[(time, ems)]

        if type == "REQ":
            milp += base_net["Net_Demand"][time][ems]*-1 + timeseries["gen"][time][ems] + dis[(time,ems)] == base_net["Net_Generation"][time][ems] + timeseries["dem"][time][ems] + char[(time,ems)]
            milp += buy[(time,ems)] == base_net["Net_Demand"][time][ems]*-1
            milp += sell[(time,ems)] == base_net["Net_Generation"][time][ems]
            milp += buy_switch[(time,ems)] == base_net["Switch_BUY"][time][ems]
            milp += sell_switch[(time,ems)] == base_net["Switch_SELL"][time][ems]
            milp += buy_switch[(time,ems)] + sell_switch[(time,ems)] <= 1


        #8. MARKET CONSTRAINT: buying and selling in same step is not possible

        #9. BATTERY_ACTIVE_VARIABLE (Logic OR-Condition)
        # milp += batt_active[(time,ems)] <= dis_switch[(time, ems)] + char_switch[(time, ems)]
        # milp += batt_active[(time,ems)] * 2 >= dis_switch[(time, ems)] + char_switch[(time, ems)]
        #
        # #10. BATTERY_STATUS_WORKAROUND (Logic AND-Condition)
        # if time == 1:
        #     milp += batt_switched_on[(time,ems)]== 0
        # else:
        #     milp += batt_switched_on[(time,ems)] >= batt_active[(time,ems)] - batt_active[(time-1,ems)]
        #     milp += batt_switched_on[(time,ems)] <= 1 - batt_active[(time-1,ems)]
        #     milp += batt_switched_on[(time,ems)] <= batt_active[(time,ems)]

        if mode == "central":
            if len(active_ems) == 9:
                milp += flex_pos[(time, active_ems[0])] + flex_pos[(time,active_ems[1])] + flex_pos[(time,active_ems[2])] + flex_pos[(time, active_ems[3])] + flex_pos[(time,active_ems[4])]  + flex_pos[(time,active_ems[5])] + flex_pos[(time, active_ems[6])] + flex_pos[(time,active_ems[7])] + flex_pos[(time,active_ems[8])]  == request_pos[time]
                milp += flex_neg[(time, active_ems[0])] + flex_neg[(time,active_ems[1])] + flex_neg[(time,active_ems[2])] + flex_neg[(time, active_ems[3])] + flex_neg[(time,active_ems[4])]  + flex_neg[(time,active_ems[5])] + flex_neg[(time, active_ems[6])] + flex_neg[(time,active_ems[7])] + flex_neg[(time,active_ems[8])] == request_neg[time]

            if len(active_ems) == 8:
                milp += flex_pos[(time, active_ems[0])] + flex_pos[(time,active_ems[1])] + flex_pos[(time,active_ems[2])] + flex_pos[(time, active_ems[3])] + flex_pos[(time,active_ems[4])]  + flex_pos[(time,active_ems[5])] + flex_pos[(time, active_ems[6])] + flex_pos[(time,active_ems[7])] == request_pos[time]
                milp += flex_neg[(time, active_ems[0])] + flex_neg[(time,active_ems[1])] + flex_neg[(time,active_ems[2])] + flex_neg[(time, active_ems[3])] + flex_neg[(time,active_ems[4])]  + flex_neg[(time,active_ems[5])] + flex_neg[(time, active_ems[6])] + flex_neg[(time,active_ems[7])] == request_neg[time]

            if len(active_ems) == 7:
                milp += flex_pos[(time, active_ems[0])] + flex_pos[(time,active_ems[1])] + flex_pos[(time,active_ems[2])] + flex_pos[(time, active_ems[3])] + flex_pos[(time,active_ems[4])]  + flex_pos[(time,active_ems[5])] + flex_pos[(time, active_ems[6])] == request_pos[time]
                milp += flex_neg[(time, active_ems[0])] + flex_neg[(time,active_ems[1])] + flex_neg[(time,active_ems[2])] + flex_neg[(time, active_ems[3])] + flex_neg[(time,active_ems[4])]  + flex_neg[(time,active_ems[5])] + flex_neg[(time, active_ems[6])] == request_neg[time]

            if len(active_ems) == 6:
                milp += flex_pos[(time, active_ems[0])] + flex_pos[(time,active_ems[1])] + flex_pos[(time,active_ems[2])] + flex_pos[(time, active_ems[3])] + flex_pos[(time,active_ems[4])]  + flex_pos[(time,active_ems[5])] == request_pos[time]
                milp += flex_neg[(time, active_ems[0])] + flex_neg[(time,active_ems[1])] + flex_neg[(time,active_ems[2])] + flex_neg[(time, active_ems[3])] + flex_neg[(time,active_ems[4])]  + flex_neg[(time,active_ems[5])] == request_neg[time]

            if len(active_ems) == 5:
                milp += flex_pos[(time, active_ems[0])] + flex_pos[(time,active_ems[1])] + flex_pos[(time,active_ems[2])] + flex_pos[(time, active_ems[3])] + flex_pos[(time,active_ems[4])] == request_pos[time]
                milp += flex_neg[(time, active_ems[0])] + flex_neg[(time,active_ems[1])] + flex_neg[(time,active_ems[2])] + flex_neg[(time, active_ems[3])] + flex_neg[(time,active_ems[4])] == request_neg[time]

            if len(active_ems) == 4:
                milp += flex_pos[(time, active_ems[0])] + flex_pos[(time,active_ems[1])] + flex_pos[(time,active_ems[2])] + flex_pos[(time, active_ems[3])] == request_pos[time]
                milp += flex_neg[(time, active_ems[0])] + flex_neg[(time,active_ems[1])] + flex_neg[(time,active_ems[2])] + flex_neg[(time, active_ems[3])] == request_neg[time]

            if len(active_ems) == 3:
                milp += flex_pos[(time, active_ems[0])] + flex_pos[(time,active_ems[1])] + flex_pos[(time,active_ems[2])] == request_pos[time]
                milp += flex_neg[(time, active_ems[0])] + flex_neg[(time,active_ems[1])] + flex_neg[(time,active_ems[2])] == request_neg[time]

            if len(active_ems) == 2:
                milp += flex_pos[(time, active_ems[0])] + flex_pos[(time,active_ems[1])] == request_pos[time]
                milp += flex_neg[(time, active_ems[0])] + flex_neg[(time,active_ems[1])] == request_neg[time]

            if len(active_ems) == 1:
                milp += flex_pos[(time, active_ems[0])] == request_pos[time]
                milp += flex_neg[(time, active_ems[0])] == request_neg[time]

    milp.solve()
    #pulp.LpSolverDefault.msg = 1
    costs = pulp.value(milp.objective)
    print("Optimization Status:{}".format(pulp.LpStatus[milp.status]))
    print("Optimization Costs:{}\n".format(pulp.value(milp.objective)))
    #print ("Costs: {}, Model_Status: {} \n".format(round(costs), run_status))

    output = []
    base = []
    for time, ems in timeseries.index:
        var_output = {
            'time': time,
            'ems': ems,
            'Net_Demand': round(buy[(time, ems)].varValue*-1,2),
            'Net_Generation': round(sell[(time, ems)].varValue,2),
            '_Demand': round(timeseries["dem"][time][ems],2),
            '_Generation': round(timeseries["gen"][time][ems]*-1,2),
            'Battery_SOC': round(cap[(time, ems)].varValue,2),
            'Battery_Charged': round(char[(time, ems)].varValue,2),
            'Battery_Discharged': round(dis[(time, ems)].varValue*-1,2),
            'Battery_Active': 0,#round(batt_active[(time, ems)].varValue,2),
            'Battery_Switched': 0,#round(batt_switched_on[(time, ems)].varValue*1,2),
            'Battery_Flexibility_POS': round(parameter[ems]["Threshold-Up"]-cap[(time, ems)].varValue,2),
            'Battery_Flexibility_NEG': round((cap[(time, ems)].varValue-parameter[ems]["Threshold-Down"])*-1,2),
            'Switch_BUY': buy_switch[(time, ems)].varValue,
            'Switch_SELL': sell_switch[(time, ems)].varValue,
            'Switch_CHAR': char_switch[(time, ems)].varValue,
            'Switch_DIS': dis_switch[(time, ems)].varValue,
            'Price_Market': timeseries["mp"][time][ems],
            'Price_Feedin': timeseries["fit"][time][ems],
            'Request_POS': round(request_pos[time],2),
            'Request_NEG': round(request_neg[time]*-1,2),
            #'flex_pos_active': flex_pos_active[(time, ems)].varValue,
            #'flex_neg_active': flex_neg_active[(time, ems)].varValue,
        }
        output.append(var_output)

    output_df = pd.DataFrame.from_records(output).sort_values(['time', 'ems'])
    output_df.set_index(['time', 'ems'], inplace=True)

    return output_df, costs
