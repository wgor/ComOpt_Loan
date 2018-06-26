from pulp import *
import random
import datetime as dt
import pandas as pd
import numpy as np

from comopt.utils import Agent
from comopt.usef_messages import Prognosis, FlexReq, FlexOffer, UDIevent

"""
Sequence of modelsteps. Gets printed within simulation output
"""
message_01 = "1.TA sent UDI-Event 'Baseline' to its attached EM-Systems.\n"
message_02 = "2.EM-System sent UDI-Event 'Baseline' to its attached TA."
message_03 = "3.TA sent prognosis with baseschedule to the MA.\n"
message_04 = "4.MA transmited back to the TA a Flex-Request as a response to the baseline prognosis.\n"
message_05 = "5.TA asked connected EM-Systems for an UDI-Event 'req_01'.\n"
message_06 = "6.EM-Systems sent UDI-Event 'req_01' to their connected TA."
message_07 = "7.TA received UDI-Events and calculated reservation price."
message_08 = "8.TA sent Flex-Offer to the MA.\n"
message_09 = "9.MA rejected Flex-Offer."
message_10 = "9.MA accepted Flex-Offer."


class Environment():
    """
    Class for the models environment.
    Within an environment agent instances of various types (e.g. Market-, Trading-, EMS-Agents) gets created and stored,
    the simulation gets proceeded stepwise and the simulation steps get tracked.
    Args:
        data:   a dictionary that provides timeseries and parameter values for the simulation. dictionary gets created by the function "data_import".
                keys and items of data: {"active_EMS": active_EMS, "ems_ts":ems_ts, "ems_p":ems_p, "MA_ts":MA_ts, "MA_param":MA_param, "TA_ts":TA_ts, "TA_param":TA_param}
        seed (optional, default:datetime): seed for the random number generators.
        name (optional, default:None): parameter to specify an environment by a given name.
    Attributes:
        running (default:True): binary variable that indicates the simulation status.
        activate_ems:   number of ems that are included in model. active ems agents can be attached or removed within the input excel file.
        running: a bool variable that is used as the on/off condition within the function "run_model".
        steps: indicates the proceeds of the model.
    """

    def __init__(self, data: "dict", seed=None, name: "str" = None):
        """
        Creates and stores environment instances.
        """
        self.name = name
        self.running = True
        self.steps = 0
        self.data = data

        # A simple list that holds EMS-INSTANCES.
        self.EMS = []
        self.MA = MarketAgent(agent_id="MA", environ=self, timeseries=self.data["MA_ts"],
                              parameters=self.data["MA_param"])
        self.TA = TradingAgent(agent_id="TA", environ=self, timeseries=self.data["TA_ts"],
                               parameters=self.data["TA_param"])

        # A str-list with NAMES OF THE EMS.(e.g."a01","a02","a03").
        self.active_EMS = data["active_EMS"]

        # The EMS-agent instances gets created.
        for agent in self.active_EMS:
            self.EMS.append(EMS(agent_id=agent, environ=self,
                                timeseries=self.data["ems_ts"][agent],
                                parameters=self.data["ems_p"][agent]))

        if seed is None:
            self.seed = dt.datetime.now()
        else:
            self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
        return

    def reset_ts(self):
        """
        Setter method to erease the ems agents timeseries data.
        """
        for agent in self.EMS:
            agent.ts[:, 4:] = 0
        return

    def run_model(self):
        """
        Run the model until the end condition is reached.
        """
        while self.running:
            self.step()
        return

    def step(self):
        """
        Gets called within run_local.py and triggers the FIRST event within the model simulation sequence.
        """
        self.TA.step()
        self.steps += 1
        return "Step Completed"


class MarketAgent(Agent):
    # Flexibility Requesting Party
    """
    The market agent (MA) represents external agents that have a need for flexibility (for example, an energy supplier or a network operator).
    Args:
        agent_id:   unique name of each EMS entity. gets automatically assigned within instantiation.
        environ:    every agent "knows" the environment he lives in. gets automatically assigned within instantiation.

    Attributes:
        ts:          holds MA timeseries data that gets specified within the input excel file. Can also be called via data["MA_ts"].
        param:       holds TA parameter data that gets specified within the input excel file. Can also be called via data["MA_param"]
        req_cnt:     counter variable that gets used to mark Flex-Request-objects.
        prognosis:   a dictionary with keys and Prognosis-Objects as items according to the respective prognosis type that the MA receives from the TA.
                     (e.g. {"base": Prognosis.type("base")})
                     => self.prognosis[name of prognosis]
        res_price:   MAs reservation price for the requested flexibility. gets calculated within the function "post_flex_order" by multiplying the requested negative and positive
                     flex energy amounts with the given balance market price prediction that the MA stores within MA.ts.loc[:,"bm_neg_price"] and MA.ts.loc[:,"bm_pos_price"].
    """

    def __init__(self, agent_id, environ, timeseries, parameters):
        """
        Creates an instance of the Class MarketAgent. Inherits from the Class Agent
        """
        super().__init__(agent_id, environ)
        self.ts = timeseries
        self.param = parameters
        self.req_cnt = 0
        self.prognosis = dict()
        self.res_price = 0
        return

    def post_flex_request(self, prognosis_type: "str", prognosis: "Prognosis-Object"):
        """
        Callback function that gets called within TAs function "post_prognosis()".
        Transmits a Flex-Request-Object to the TA in return for a Prognosis-Object.
        Amount of requested energy gets equally divided and the shares then later gets passed to the active EM-Systems.
        """
        flex_req = FlexReq()
        if prognosis_type == "base":
            self.prognosis["base"] = prognosis
            flex_req.id = "req_base"
            flex_req.values["pos"] = self.ts.loc[:, 'req_pos'] / len(self.environ.active_EMS)
            flex_req.values["neg"] = self.ts.loc[:, 'req_neg'] / len(self.environ.active_EMS)
            self.req_cnt += 1
            print(message_04)
        return flex_req

    def post_flex_order(self, flex_offer):
        """
        Callback function that gets called within TAs function "post_flex_offer()".
        Transmits a Flex-Order-Object to the TA in return for a Flex-Offer-Object.
        """
        for t in self.ts.index:
            self.res_price += self.ts.loc[t, "req_neg"] * self.ts.loc[t, "bm_neg_price"] + \
                              self.ts.loc[t, "req_pos"] * self.ts.loc[t, "bm_pos_price"]
        if self.res_price < flex_offer.price:
            print(message_09)
        else:
            print(message_10)
        return print("MA reservation price: {}".format(self.res_price))


class TradingAgent(Agent):
    """
    Aggregator-type like entity who acts as an intermediate agent between an the market agent and the prosumer agents (represented through EMS).
    Collects, aggregates and trades flexibility.
    Args:
        agent_id:   unique name of each EMS entity. gets automatically assigned within instantiation.
        environ:    every agent "knows" the environment he lives in. gets automatically assigned within instantiation.

    Attributes:
        ts:         holds TA timeseries data that gets specified within the input excel file. Can also be called via data["TA_ts"].
        param:      holds TA parameter data that gets specified within the input excel file. Can also be called via data["TA_param"]
        UDI_events: a dictionary with keys and items according to the respective UDI-events type that the TA receives from its EM-Systems.
                    e.g. {"baselines": (EMS[0].UDIevent.type("base"), EMS[1].UDIevent.type("base"),..)}
                            => for every UDI-Event-Type there's one UDI-Event per agent
                            => UDI-Event-Objects are callable through: self.UDI_events[name of the UDI-Event][ems.agent_id]
                    UDI-Events-Objects gets instaniated by the EM-Systems and gets stored within the TAs scope by calling TAs function "post_device_message()",
                    which has the EM-System function "post_UDI_event()" encapsulated as a callback.

        prognosis:  a dictionary with keys and items according to the respective prognosis type that the TA transmits from the TA.(e.g. {"base": Prognosis.type("base")})
        prognosis_cnt: counter variable that gets used to identify Flex-Request-objects.
        flex_req:   a dictionary with keys and Flex-Request-Objects as items according to the respective Flex-Requests that the MA has sent to the TA.
                    => Flex-Request-Objects are callable through: self.flex_req[name of the Flex-request], e.g. self.flex_req[]
                    Flex-Request-objects gets instaniated by the MA and gets stored into the TAs scope by calling TAs function "post_prognosis()",
                    which has the MAs function "post_flex_request()"" encapsulated as a callback.
        flex_offers: a dictionary with keys and Flex-offer-Objects as items, according to the respective Flex-Offers that the TA has sent to the MA.
                    Flex-Offer-Objects gets instaniated by the TA by calling TAs function "post_flex_offer()",
                    which has the MA function "post_flex_order()" encapsulated as a callback.
        flex_offer_cnt: counter variable that gets used to identify Flex-Offer-objects.
    """

    def __init__(self, agent_id, environ, timeseries, parameters):
        """
        Creates an instance of the Class TradingAgent. Inherits from the Class Agent.
        """
        super().__init__(agent_id, environ)
        self.ts = timeseries
        self.param = parameters
        self.UDI_events = dict()
        self.prognosis = dict()
        self.prognosis_cnt = 0
        self.flex_req = dict()
        self.flex_offers = dict()
        self.flex_offer_cnt = 0
        return

    def post_device_message(self, message_type: "str", flex_req: "FlexReq-Obj"):
        """
        Asks EM-Systems for UDI-events, by calling their "post_UDI_event()"-function.
        There's no specific "device-message-objects" within the model.
        """
        if message_type == "base":
            print(message_01)
            self.UDI_events["baselines"] = {}
            for ems in self.environ.EMS:
                self.UDI_events["baselines"][ems.agent_id] = ems.post_UDI_event(type="base", flex_req=None)

        if message_type == "req":
            print(message_05)
            self.UDI_events["req"] = {}
            for ems in self.environ.EMS:
                self.UDI_events["req"][ems.agent_id] = ems.post_UDI_event(type="req", flex_req=self.flex_req["req"])
            return

    def post_prognosis(self, prognosis_type):
        """
        Sends Prognosis-Object to MA and concurrently asks for Flex-Requests,
        by calling MAs "post_flex_request()"-function.
        Prognosis-Object gets the sum of all agents purchased and sold energy as value input,
        as well as the prices and remunerations paid and received for those energy amounts.
        """
        if prognosis_type == "base":
            self.prognosis["base"] = Prognosis(id=self.prognosis_cnt, prognosis_type="base")
            self.prognosis_cnt += 1
            buy_sum_df = pd.DataFrame()
            buy_costs_df = pd.DataFrame()
            sell_sum_df = pd.DataFrame()
            sell_rev_df = pd.DataFrame()
            for ems in self.environ.EMS:
                buy_sum_df[ems.agent_id] = self.UDI_events["baselines"][ems.agent_id].values.loc[:, "buy"]
                buy_costs_df[ems.agent_id] = self.UDI_events["baselines"][ems.agent_id].values.loc[:, "buy"] \
                    .multiply(self.UDI_events["baselines"][ems.agent_id].values.loc[:, "mp"])
                sell_sum_df[ems.agent_id] = self.UDI_events["baselines"][ems.agent_id].values.loc[:, "sell"]
                sell_rev_df[ems.agent_id] = self.UDI_events["baselines"][ems.agent_id].values.loc[:, "sell"] \
                    .multiply(self.UDI_events["baselines"][ems.agent_id].values.loc[:, "fp"])
            self.prognosis["base"].values["from_grid"] = buy_sum_df.sum(axis=1)
            self.prognosis["base"].values["to_grid"] = sell_sum_df.sum(axis=1)
            self.prognosis["base"].costs = buy_costs_df.sum(axis=1)
            self.prognosis["base"].revs = sell_rev_df.sum(axis=1)
            print(message_03)
            self.flex_req["req"] = self.environ.MA.post_flex_request(prognosis=self.prognosis["base"],
                                                                     prognosis_type="base")
            return

    def calc_flex_req_costs(self):
        """
        Calculates the difference between UDI-Event "Baseline" and UDI-Event "Request for each agents,
        and sums up all the costs and revenue losses.
        """
        print(message_07)
        total_costs_flex_req = 0
        for i, j, k in zip(self.UDI_events["baselines"], self.UDI_events["req"], self.UDI_events["baselines"].keys()):
            if self.UDI_events["baselines"][i].costs > 0:
                diff = self.UDI_events["baselines"][i].costs - self.UDI_events["req"][j].costs
                print("EMS '{}' Costs changed: ".format(k))
                print(diff * -1)
                print("")
                total_costs_flex_req += diff * -1
            elif self.UDI_events["baselines"][i].costs < 0:
                diff = self.UDI_events["baselines"][i].costs - self.UDI_events["req"][j].costs
                print("EMS '{}' Revenues changed: ".format(k))
                print(diff)
                print("")
                total_costs_flex_req += diff * -1
        print("=> Total Costs for Flex-Request: {} <=\n".format(total_costs_flex_req))
        return total_costs_flex_req

    def post_flex_offer(self):
        """
        Calls TAs function "calc_flex_req_costs()" in order to come up with an flex_offer_price, and then posts this price to the MA
        """
        flex_offer = FlexOffer()
        flex_offer.id = self.flex_offer_cnt
        flex_offer.flex_req_id = self.flex_req["req"].id
        flex_offer.price = self.calc_flex_req_costs()
        print(message_08)
        self.environ.MA.post_flex_order(flex_offer)
        self.flex_offer_cnt += 1
        return

    def step(self):
        """
        Actual Sequence of events that occur within one model step.
        TA's step function gets called upfront within the environments step function.
        """
        self.post_device_message("base", flex_req=None)
        self.post_prognosis(prognosis_type="base")
        self.post_prognosis(prognosis_type="req")
        self.post_device_message(message_type='req', flex_req=self.flex_req["req"])
        self.post_flex_offer()
        return


class EMS(Agent):
    """
    Prosumer-type agents that has several (shiftable) consumer devices like photopholtaics, batteries, EV,
    etc. attached. Represented as an EM-System, instances of this class holds consumption and generation
    timeseries and device parameters which can be used to calculate (optimal) energy management schedules.

    Args:
        agent_id:   unique name of each EMS entity. gets automatically assigned within instantiation.
        environ:    every agent "knows" the environment he lives in. gets automatically assigned within instantiation.

    Attributes:
        ts:         holds TA timeseries data that gets specified within the input excel file. Can also be called via ems_ts[a[1]].
        param:      holds TA parameter data that gets specified within the input excel file. Can also be called via data["TA_param"].
        UDI_events: a dictionary with keys and items according to the respective UDI-events type that the TA receives from its EM-Systems.
                e.g. {"baselines": (EMS[0].UDIevent.type("base"), EMS[1].UDIevent.type("base"),..)}
                        => for every UDI-Event-Type there's one UDI-Event per agent
                        => UDI-Event-Objects are callable through: self.UDI_events[name of the UDI-Event][ems.agent_id]
                UDI-Events-Objects gets instaniated by the EM-Systems and gets stored within the TAs scope by calling TAs function "post_device_message()",
                which has the EM-System function "post_UDI_event()" encapsulated as a callback.
    self.costs: a dictionary that holds the costs output from the milp-optimization for each run
    """

    # An agent with gen, battery and load profile
    def __init__(self, agent_id, environ, timeseries, parameters):
        super().__init__(agent_id, environ)
        self.ts = timeseries
        self.params = parameters
        self.UDI_events = dict()
        self.UDI_event_id = 0
        self.costs = dict()

    def post_UDI_event(self, type, flex_req):
        """
        Creates an UDI-Event-Object and writes the output of the optimization on it.
        """
        id = self.UDI_event_id
        UDI_event = UDIevent(id)
        if type == "base":
            print(message_02)
            output = self.milp_solver(type="base", flex_req=None)
            UDI_event.type = "base"
            UDI_event.values = output[0]
            UDI_event.costs = output[1]
            self.UDI_events[type] = UDI_event
            self.UDI_event_id += 1
        elif type == "req":
            print(message_06)
            output = self.milp_solver(type="req", flex_req=flex_req)
            UDI_event.type = "req"
            UDI_event.values = output[0]
            UDI_event.costs = output[1]
            self.UDI_events[type] = UDI_event
            self.UDI_event_id += 1
        return UDI_event

    def milp_solver(self, type, flex_req):
        # prob variable
        run_costs = 0
        run_status = 0
        lpmodel = pulp.LpProblem("Test", pulp.LpMinimize)
        if type == "base":
            print("Run:Baseline - EMS:{}".format(self.agent_id))
        elif type == "req":
            print("Run:Request - EMS:{}".format(self.agent_id))

        # VARIABLES
        buy = pulp.LpVariable.dicts("buy", self.ts.index, 0, upBound=self.params.loc["max_buy"], cat="NonNegativeReals")
        sell = pulp.LpVariable.dicts("sell", self.ts.index, 0, upBound=self.params.loc["max_sell"],
                                     cat="NonNegativeReals")
        cap = pulp.LpVariable.dicts("batt_cap", self.ts.index, lowBound=self.params.loc["thres_down"],
                                    upBound=self.params.loc["thres_up"], cat="NonNegativeReals")
        dis = pulp.LpVariable.dicts("discharged", self.ts.index, cat="NonNegativeReals")
        char = pulp.LpVariable.dicts("charged", self.ts.index, cat="NonNegativeReals")
        buy_switch = pulp.LpVariable.dicts("state_buy", self.ts.index, cat="Binary")
        sell_switch = pulp.LpVariable.dicts("state_sell", self.ts.index, cat="Binary")
        dis_switch = pulp.LpVariable.dicts("stat_dis", self.ts.index, cat="Binary")
        char_switch = pulp.LpVariable.dicts("stat_char", self.ts.index, cat="Binary")

        ############################ OBJECTIVE ################################
        lpmodel += pulp.lpSum(buy[t] * self.ts.mp[t] - sell[t] * self.ts.fp[t] for t in self.ts.index)
        #################### BASELINE CONSTRAINTS #############################
        for t in self.ts.index:
            # BATTERY CONSTRAINT 1: charging or discharging in t
            lpmodel += dis_switch[t] + char_switch[t] <= 1
            # BATTERY CONSTRAINT 2: char and dischar limits, if stat is 1
            lpmodel += self.params.min_dis * dis_switch[t] <= dis[t]
            lpmodel += self.params.max_dis * dis_switch[t] >= dis[t]
            lpmodel += self.params.min_cha * char_switch[t] <= char[t]
            lpmodel += self.params.max_cha * char_switch[t] >= char[t]
            # BATTERY CONSTRAINT 4: battery cap must be between low and high threshold
            lpmodel += cap[t] >= self.params.thres_down
            lpmodel += cap[t] <= self.params.thres_up
            # BATTERY CONSTRAINT 5: Init and End State of BatteryCap
            past = t - 1
            if t == min(self.ts.index):
                lpmodel += cap[min(self.ts.index)] == self.params.initSOC
            else:
                lpmodel += cap[t] == cap[past] - dis[t] + char[t]
            if t == max(self.ts.index):
                lpmodel += cap[t] == self.params.endSOC
            # BALANCING CONSTRAINT: buy + gen + dis + req_up == bought + demand + char per step
            lpmodel += buy[t] + self.ts.gen[t] + dis[t] == sell[t] + self.ts.dem[t] + char[t]
            # MARKET CONSTRAINT 1: maximum buy and sell quantity per step
            lpmodel += buy[t] <= self.params.max_buy * buy_switch[t]
            lpmodel += sell[t] <= self.params.max_sell * sell_switch[t]
            # MARKET CONSTRAINT 2: buying and selling in same step is not possible
            lpmodel += buy_switch[t] + sell_switch[t] <= 1
            # print (lpmodel.constraints)
            # FLEXREQUEST Contraints
            if type == "req":
                if flex_req.values["neg"].loc[t] != 0:
                    lpmodel += dis[t] == flex_req.values["neg"].loc[t]
                elif flex_req.values["pos"].loc[t] != 0:
                    lpmodel += char[t] == flex_req.values["pos"].loc[t]
        # LpSolverDefault.msg = 1
        lpmodel.solve()
        run_costs = pulp.value(lpmodel.objective)
        run_status = pulp.LpStatus[lpmodel.status]

        if flex_req != None:
            print("Flex_Request: {}".format(str(flex_req)))
            print("Costs: {}".format(run_costs))
            self.costs["Flex_Request"] = pulp.value(lpmodel.objective)
            if self.costs["Flex_Request"] < 0:
                print("Change in Revenues: {}\n".format(self.costs["Baseline"] - run_costs))
            elif self.costs["Flex_Request"] > 0:
                print("Change in Costs: {}\n".format(run_costs - self.costs["Baseline"]))
        elif flex_req == None:
            self.costs["Baseline"] = pulp.value(lpmodel.objective)
            print("No Flex Req.")
            print("Costs/Revenues: {}\n".format(run_costs))

        ## WRITE OUTPUT DATA TO AGENT's TS
        for t in self.ts.index:
            self.ts.loc[t, "sell"] = sell[t].varValue * -1
            self.ts.loc[t, "buy"] = buy[t].varValue
            self.ts.loc[t, "cap"] = cap[t].varValue
            self.ts.loc[t, "buy_switch"] = buy_switch[t].varValue
            self.ts.loc[t, "sell_switch"] = sell_switch[t].varValue
            self.ts.loc[t, "char_switch"] = char_switch[t].varValue
            self.ts.loc[t, "dis_switch"] = dis_switch[t].varValue
            self.ts.loc[t, "char"] = char[t].varValue
            self.ts.loc[t, "dis"] = dis[t].varValue * -1
            self.ts.loc[t, "batt_flex_up"] = self.params.loc["thres_up"] - cap[t].varValue
            self.ts.loc[t, "batt_flex_down"] = cap[t].varValue - self.params.loc["thres_down"]
        ## save actual batt cap for next period
        # lastcap = cap[max(self.ts.index)].varValue
        # data_export("ComOpt.xlsm", self, run_costs, run_status)
        return self.ts, run_costs
