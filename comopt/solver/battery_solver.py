import pandas as pd
import pulp


def battery_solver(
    name,
    multi_ix_df,
    parameter,
    flex_request,
    flags,
    timeperiods,
    type,
    mode,
    active_ems,
    base_net,
):
    """
    name:
        Name of request e.g. "BASE","REQ_1"
    multi_ix_df:
        timeseries files with pandas multiindizes "time","ems".
    parameter:
        Features or options for EM-Systems e.g. "Generation-Profile", "Maximum Battery Charging Rate"
    flex_request:
        List with flex request values for each timeperiod. Contains negative, positive or zero values.
    flags:
        Options or features set within the user interfaceself.
    timeperiods:
        List with range of timeperiod values.
    type:
        Argument values could be "REQ" or "BASE".
        Determines whether the base profile without requests or a flex request gets solved.
    mode:
        Argument values could be "central" or "flex-split".
        Within mode "central" all EM-System timeseries gets aggregated and flex requests get shared omtimally by the solver (without internal balancing).
        Within mode "flex-split" each EM-System gets a share of the flex request upfront and then solves the scheduling problem (without internal balancing).
    active_ems:
        List with names of active EM-Systems.
    base_net:
        Net demand and net generation baseline values of all active EM-Systems.
    """
    # old to do: Find efficient way to iterate over active ems in order to assign flex_request LpVariables(see file origin_solver).

    timeseries = multi_ix_df
    parameter = pd.DataFrame(parameter)
    request_pos = pd.Series(0, index=timeperiods).astype("float64")
    request_neg = pd.Series(0, index=timeperiods).astype("float64")
    costs = 0
    battery_flexibility = None

    try:
        flags.loc["Batteries", "EMS"]
        battery_flexibility = "Yes"
    except:
        print("No battery choosen!")
        return

    if type == "REQ":
        for val, time in zip(flex_request.values, timeperiods):
            if val > 0:
                request_pos[time] = val
            if val < 0:
                request_neg[time] = val * -1

    milp = pulp.LpProblem("Cost minimising scheduling problem", pulp.LpMinimize)
    # data dat gets passed in

    ############################ VARIABLES ################################

    buy = pulp.LpVariable.dicts(
        "buy",
        ((time, ems) for time, ems in timeseries.index),
        lowBound=0,
        cat="NonNegativeReals",
    )
    sell = pulp.LpVariable.dicts(
        "sell",
        ((time, ems) for time, ems in timeseries.index),
        lowBound=0,
        cat="NonNegativeReals",
    )
    cap = pulp.LpVariable.dicts(
        "cap", ((time, ems) for time, ems in timeseries.index), cat="NonNegativeReals"
    )
    dis = pulp.LpVariable.dicts(
        "dis", ((time, ems) for time, ems in timeseries.index), cat="NonNegativeReals"
    )
    char = pulp.LpVariable.dicts(
        "char", ((time, ems) for time, ems in timeseries.index), cat="NonNegativeReals"
    )
    buy_switch = pulp.LpVariable.dicts(
        "buy_switch", ((time, ems) for time, ems in timeseries.index), cat="Binary"
    )
    sell_switch = pulp.LpVariable.dicts(
        "sell_switch", ((time, ems) for time, ems in timeseries.index), cat="Binary"
    )
    dis_switch = pulp.LpVariable.dicts(
        "dis_switch", ((time, ems) for time, ems in timeseries.index), cat="Binary"
    )
    char_switch = pulp.LpVariable.dicts(
        "char_switch", ((time, ems) for time, ems in timeseries.index), cat="Binary"
    )
    batt_active = pulp.LpVariable.dicts(
        "batt_active", ((time, ems) for time, ems in timeseries.index), cat="Binary"
    )
    batt_switched_on = pulp.LpVariable.dicts(
        "batt_switched_on",
        ((time, ems) for time, ems in timeseries.index),
        cat="Binary",
    )

    ############################ OBJECTIVE ################################
    if type == "BASE":
        milp += pulp.lpSum(
            [
                buy[(time, ems)] * timeseries["mp"][time][ems]
                - sell[(time, ems)] * timeseries["fit"][time][ems]
                + batt_switched_on[(time, ems)] * parameter[ems]["Start-Up-Costs"]
                for time, ems in timeseries.index
            ]
        )

    if type == "REQ":
        milp += pulp.lpSum(
            [
                (request_pos[time] - char[(time, ems)])
                + (request_neg[time] - dis[(time, ems)])
                for time, ems in timeseries.index
            ]
        )

    #################### BASELINE CONSTRAINTS #############################
    for time, ems in timeseries.index:
        """ access LpVariable: e.g. buy[time,ems]
            access data from "outside": e.g timeseries["gen"][time][ems]"""

        # CONSTRAINT Battery: Either charging or discharging in every timestep
        milp += dis_switch[(time, ems)] + char_switch[(time, ems)] <= 1

        # CONSTRAINT Battery: Min/Max charging rates and Min/Max discharging rates [in kW]
        milp += (
            parameter[ems]["Discharge-Min"] * dis_switch[(time, ems)]
            <= dis[(time, ems)]
        )
        milp += (
            parameter[ems]["Discharge-Max"] * dis_switch[(time, ems)]
            >= dis[(time, ems)]
        )
        milp += (
            parameter[ems]["Charge-Min"] * char_switch[(time, ems)] <= char[(time, ems)]
        )
        milp += (
            parameter[ems]["Charge-Max"] * char_switch[(time, ems)] >= char[(time, ems)]
        )

        # CONSTRAINT Battery: Storage capacity must be between low and high thresholds in every timestep.
        milp += (
            cap[(time, ems)] >= parameter[ems]["Threshold-Down"]
        )  # parameter[ems]["Threshold-Down"]
        milp += (
            cap[(time, ems)] <= parameter[ems]["Threshold-Up"]
        )  # parameter[ems]["Threshold-Up"]

        # CONSTRAINT Battery: Init and End State of Battery Cap constraints, capacity at every step.
        if time == 1:
            milp += (
                cap[(1, ems)]
                == parameter[ems]["Battery-SOC-Init"]
                - dis[(time, ems)]
                + char[(time, ems)]
            )
        else:
            milp += (
                cap[(time, ems)]
                == cap[(time - 1, ems)] - dis[(time, ems)] + char[(time, ems)]
            )

        # CONSTRAINT BALANCING : buy + gen + dis + req_up == bought + demand + char per step
        # CONSTRAINT MARKET : buying and selling in same step is not possible
        if type == "BASE":
            milp += (
                buy[(time, ems)]
                + timeseries["gen"][time][ems]
                + dis[(time, ems)]
                + request_neg[time]
                == sell[(time, ems)]
                + timeseries["dem"][time][ems]
                + char[(time, ems)]
                + request_pos[time]
            )
            milp += buy_switch[(time, ems)] + sell_switch[(time, ems)] <= 1
            milp += (
                buy[(time, ems)]
                <= parameter[ems]["Buying-Max"] * buy_switch[(time, ems)]
            )
            milp += (
                sell[(time, ems)]
                <= parameter[ems]["Selling-Max"] * sell_switch[(time, ems)]
            )

        if type == "REQ":
            milp += (
                base_net["Net_Demand"][time][ems] * -1
                + timeseries["gen"][time][ems]
                + dis[(time, ems)]
                == base_net["Net_Generation"][time][ems]
                + timeseries["dem"][time][ems]
                + char[(time, ems)]
            )
            milp += buy[(time, ems)] == base_net["Net_Demand"][time][ems] * -1
            milp += sell[(time, ems)] == base_net["Net_Generation"][time][ems]
            milp += buy_switch[(time, ems)] == base_net["Switch_BUY"][time][ems]
            milp += sell_switch[(time, ems)] == base_net["Switch_SELL"][time][ems]
            milp += buy_switch[(time, ems)] + sell_switch[(time, ems)] <= 1

        # CONSTRAINT BATTERY_ACTIVE_VARIABLE (Logic OR-Condition)
        milp += (
            batt_active[(time, ems)]
            <= dis_switch[(time, ems)] + char_switch[(time, ems)]
        )
        milp += (
            batt_active[(time, ems)] * 2
            >= dis_switch[(time, ems)] + char_switch[(time, ems)]
        )

        # CONSTRAINT BATTERY_STATUS_WORKAROUND (Logic AND-Condition)
        if time == 1:
            milp += batt_switched_on[(time, ems)] == 0
        else:
            milp += (
                batt_switched_on[(time, ems)]
                >= batt_active[(time, ems)] - batt_active[(time - 1, ems)]
            )
            milp += batt_switched_on[(time, ems)] <= 1 - batt_active[(time - 1, ems)]
            milp += batt_switched_on[(time, ems)] <= batt_active[(time, ems)]

    milp.solve()

    costs = pulp.value(milp.objective)
    print("Optimization Status:{}".format(pulp.LpStatus[milp.status]))
    print("Optimization Costs:{}\n".format(pulp.value(milp.objective)))

    output = []
    for time, ems in timeseries.index:
        var_output = {
            "time": time,
            "ems": ems,
            "Net_Demand": round(buy[(time, ems)].varValue * -1, 2),
            "Net_Generation": round(sell[(time, ems)].varValue, 2),
            "_Demand": round(timeseries["dem"][time][ems], 2),
            "_Generation": round(timeseries["gen"][time][ems] * -1, 2),
            "Battery_SOC": round(cap[(time, ems)].varValue, 2),
            "Battery_Charged": round(char[(time, ems)].varValue, 2),
            "Battery_Discharged": round(dis[(time, ems)].varValue * -1, 2),
            "Battery_Active": round(batt_active[(time, ems)].varValue, 2),
            "Battery_Switched": round(batt_switched_on[(time, ems)].varValue * 1, 2),
            "Battery_Flexibility_POS": round(
                parameter[ems]["Threshold-Up"] - cap[(time, ems)].varValue, 2
            ),
            "Battery_Flexibility_NEG": round(
                (cap[(time, ems)].varValue - parameter[ems]["Threshold-Down"]) * -1, 2
            ),
            "Switch_BUY": buy_switch[(time, ems)].varValue,
            "Switch_SELL": sell_switch[(time, ems)].varValue,
            "Switch_CHAR": char_switch[(time, ems)].varValue,
            "Switch_DIS": dis_switch[(time, ems)].varValue,
            "Price_Market": timeseries["mp"][time][ems],
            "Price_Feedin": timeseries["fit"][time][ems],
            "Request_POS": round(request_pos[time], 2),
            "Request_NEG": round(request_neg[time] * -1, 2),
        }
        output.append(var_output)

    output_df = pd.DataFrame.from_records(output).sort_values(["time", "ems"])
    output_df.set_index(["time", "ems"], inplace=True)

    return output_df, costs
