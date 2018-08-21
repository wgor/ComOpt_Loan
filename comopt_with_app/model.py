from solver import solver
from messages import Prognosis, FlexReq, FlexOffer, FlexOrder, UDIevent
from pulp import *
from globals import *
from globals import global_last_request_costs
#from app import *
import random
import datetime as dt
import xlwings as xw
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pickle

############## Test Branch End ################

''' Sequence of modelsteps. Gets printed within simulation output'''
message_01 = "1.TA calls its attached EM-Systems to send a UDI-Event 'BASE'.\n"
message_02 = "2.EMS received call for UDI-Event 'BASE'.\n"
message_03 = "3.EM-Systems sent UDI-Event 'BASE' to its attached TA.\n"
message_04 = "4.TA sends prognosis to the MA.\n"
message_05 = "5.MA transmits a Flex-Request back to the TA.\n"
message_06 = "6.TA asks connected EM-System for an UDI-Event 'REQ'.\n"
message_07 = "7.EMS received call for UDI-Event 'REQ'.\n"
message_08 = "8.EM-System sent UDI-Event 'REQ' to their connected TA.\n"
message_09 = "9.TA received UDI-Events and calculated reservation price."
message_10 = "10.TA sent Flex-Offer to the MA.\n"
message_11 = "11.MA rejected Flex-Offer.\n"
message_12 = "12.MA accepted Flex-Offer.\n"

######################### CLASSES #########################
class Agent:
    """ Base class for a model agent. """
    def __init__(self, agent_id, environ):
        """ Create a new agent. """
        self.agent_id = agent_id
        self.environ = environ

    def step(self):
        """ A single step of the agent. """
        pass

class Environment():
    """ Class for the models environment.
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
    def __init__(self,run_name, timeseries, parameter, active_ems, scenario, timeperiods, seed=None):
        ''' Creates and stores environment instances.'''

        self.running = True
        self.steps = 0
        self.run_name = run_name

        self.list_of_active_ems = active_ems
        self.timeperiods = timeperiods
        self.optimization_mode = parameter["flags"]["TA"]["Optimization"]
        self.EMS = []
        self.MA = MarketAgent(agent_id="MA", environ=self, timeseries=timeseries, parameter=parameter)
        self.TA = TradingAgent(agent_id="TA", environ=self,timeseries=timeseries, parameter=parameter)

        for ems in self.list_of_active_ems:
            self.EMS.append(EMS(agent_id=ems, environ=self, timeseries=timeseries, parameter=parameter))

        if seed is None:
            self.seed = dt.datetime.now()
        else:
            self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
        return

    def run_model(self):
        ''' Run the model until the end condition is reached.'''
        while self.running:
            self.step()
        return

    def step(self):
        ''' Gets called within run_opt.py and triggers the FIRST event within the model simulation sequence.'''
        self.TA.step()
        self.steps += 1
        return self.TA.optimization_outputs
#------------------------------------------------------------------------------MARKET AGENT----------------------------------------------------------------------------------------#
class MarketAgent(Agent):
    # Flexibility Requesting Party
    ''' The market agent (MA) represents external agents that have a need for flexibility (for example, an energy supplier or a network operator).
    Args:
        agent_id:   unique name of each EMS entity. gets automatically assigned within instantiation.
        environ:    every agent "knows" the environment he lives in. gets automatically assigned within instantiation.

    Attributes:
        ts:          holds MA timeseries data that gets specified within the input excel file. Can also be called via data["MA_ts"].
        param:       holds TA parameter data that gets specified within the input excel file. Can also be called via data["MA_param"]
        req_cnt:     counter variable that gets used to mark Flex-Request-objects.
        prognosis:   a dictionary with keys and Prognosis-Objects as items according to the respective prognosis type that the MA receives from the TA.
                     (e.g. {"BASE": Prognosis.type("BASE")})
                     => self.prognosis[name of prognosis]
        res_price:   MAs reservation price for the requested flexibility. gets calculated within the function "post_flex_order" by multiplying the requested negative and positive
                     flex energy amounts with the given balance market price prediction that the MA stores within MA.ts.loc[:,"bm_neg_price"] and MA.ts.loc[:,"bm_pos_price"].
    '''

    def __init__(self, agent_id, environ, timeseries, parameter):
        ''' Creates an instance of the Class MarketAgent. Inherits from the Class Agent '''
        super().__init__(agent_id, environ)
        self.flex_requests = timeseries["ma"]
        self.req_cnt = 1
        self.prognosis = dict()
        self.res_price = 0
        return

    def post_flex_request(self, prognosis_type: "str", prognosis: "Prognosis-Object"):
        ''' Callback function that gets called within TAs function "post_prognosis()". Transmits a Flex-Request-Object to the TA in return for a Prognosis-Object.
            Amount of requested energy gets equally divided and the shares then later gets passed to the active EM-Systems.
        '''
        flex_request = FlexReq()
        if prognosis_type == "BASE":
            self.prognosis["BASE"] = prognosis
            flex_request.id = "FLEX_REQUESTS"
            flex_request.values = self.flex_requests
            self.req_cnt += 1
            print(message_05)
        return flex_request

    def post_flex_order(self, flex_offer):
        ''' Callback function that gets called within TAs function "post_flex_offer()".
        Transmits a Flex-Order-Object to the TA in return for a Flex-Offer-Object.'''
        print(message_10)
        return #print ("MA reservation price: {}".format(self.res_price))
#------------------------------------------------------------------------------TRADING AGENT----------------------------------------------------------------------------------------#
class TradingAgent(Agent):
    """ Aggregator-type like entity who acts as an intermediate agent between an the market agent and the prosumer agents (represented through EMS).
        Collects, aggregates and trades flexibility.
    Args:
        agent_id:   unique name of each EMS entity. gets automatically assigned within instantiation.
        environ:    every agent "knows" the environment he lives in. gets automatically assigned within instantiation.

    Attributes:
        ts:         holds TA timeseries data that gets specified within the input excel file. Can also be called via data["TA_ts"].
        param:      holds TA parameter data that gets specified within the input excel file. Can also be called via data["TA_param"]
        UDI_events: a dictionary with keys and items according to the respective UDI-events type that the TA receives from its EM-Systems.
                    e.g. {"BASE": (EMS[0].UDIevent.type("BASE"), EMS[1].UDIevent.type("BASE"),..)}
                            => for every UDI-Event-Type there's one UDI-Event per agent
                            => UDI-Event-Objects are callable through: self.UDI_events[name of the UDI-Event][ems.agent_id]
                    UDI-Events-Objects gets instaniated by the EM-Systems and gets stored within the TAs scope by calling TAs function "post_device_message()",
                    which has the EM-System function "post_UDI_event()" encapsulated as a callback.

        prognosis:  a dictionary with keys and items according to the respective prognosis type that the TA transmits from the TA.(e.g. {"BASE": Prognosis.type("BASE")})
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

    def __init__(self, agent_id, environ, timeseries, parameter):
        ''' Creates an instance of the Class TradingAgent. Inherits from the Class Agent.'''
        super().__init__(agent_id, environ)
        #self.parameter = parameter[scenario]["flags"]["TA"]["Optimization"]
        #print(parameter[scenario]["flags"]["TA"]["Optimization"])
        self.timeseries = timeseries["ta"]
        self.flags = parameter["flags"]
        self.flex_split_mode = parameter["flags"]["TA"]["Flex_Request_Split"]
        self.optimization_mode = parameter["flags"]["TA"]["Optimization"]
        self.internal_balance = parameter["flags"]["TA"]["Internal_Balance"]
        self.UDI_events = dict()
        self.UDI_events["OFFERS"] = dict()
        self.prognosis= dict()
        self.prognosis_cnt = 0
        self.flex_requests = dict()
        self.flex_offers = dict()
        self.flex_offer_cnt = 0
        self.optimization_outputs = dict()
        self.random_datasets = dict()
        self.parameter_ems = dict()
        self.multi_ix_df = None
        self.base_net_df = None

    def central_optimization(self, type):
        if type == "BASE":
            solver_output = solver(name="BASE",
                                    multi_ix_df=self.multi_ix_df,
                                    parameter=self.parameter_ems,
                                    flex_request=None,
                                    flags=self.flags,
                                    timeperiods = self.environ.timeperiods,
                                    type="BASE",
                                    mode="central",
                                    active_ems=self.environ.list_of_active_ems,
                                    base_net = None)
            self.optimization_outputs["BASE"] = dict()
            self.optimization_outputs["BASE"]["timeseries"] = solver_output[0]
            self.optimization_outputs["BASE"]["costs"] = solver_output[1]
            self.base_net_df = self.optimization_outputs["BASE"]["timeseries"].loc[:,["buy", "sell"]]
            print(self.optimization_outputs.keys())

        if type == "FLEX_REQ":
            all_requests = self.flex_requests.values
            all_offers = global_offer_names[1:]
            print("Print ALL OFFERS:{}\n".format(all_offers))
            for request, offer in zip(all_requests.keys(), all_offers):
                if "REQ" in request:
                    solver_output = solver(name=request,
                                            multi_ix_df=self.multi_ix_df,
                                            parameter=self.parameter_ems,
                                            flex_request = all_requests[request],
                                            flags=self.flags,
                                            timeperiods = self.environ.timeperiods,
                                            type="REQ",
                                            mode="central",
                                            active_ems=self.environ.list_of_active_ems,
                                            base_net = self.base_net_df)
                    self.optimization_outputs[offer] = dict()
                    self.optimization_outputs[offer]["timeseries"] = solver_output[0]
                    self.optimization_outputs[offer]["costs"] = solver_output[1]
                    print(self.optimization_outputs.keys())
        return

    def post_device_message(self, message_type: "str", flex_req:"FlexReq-Obj", random_nr = None):
        ''' Asks EM-Systems for UDI-events, by calling their "post_UDI_event()"-function. Theres no specific "device-message-objects" within the model. '''

        if message_type == "BASE":
            ################
            print(message_01)
            ################
            try:
                self.UDI_events["BASE"]
            except:
                for offer in global_offer_names:
                    self.UDI_events[offer] = {}
                    self.optimization_outputs[offer] = dict()
                    self.optimization_outputs[offer]["timeseries"] = dict()
                    self.optimization_outputs[offer]["costs"] = dict()

            costs = dict()
            for ems in self.environ.EMS:
                self.UDI_events["BASE"][ems.agent_id] = ems.post_UDI_event(type="BASE", flex_req=None)
                df = self.UDI_events["BASE"][ems.agent_id].values
                self.optimization_outputs["BASE"]["costs"][ems.agent_id] = self.UDI_events["BASE"][ems.agent_id].costs
                try:
                    ts_multi_ix
                except:
                    ts_multi_ix = pd.MultiIndex.from_product([global_timeperiods, self.environ.list_of_active_ems], names=['time', 'ems'])
                    ts_multi_ix_df = pd.DataFrame(index=ts_multi_ix, columns=self.UDI_events["BASE"][ems.agent_id].values.columns)
                ts_multi_ix_df = pd.concat([ts_multi_ix_df, df], axis = 0, levels=1).sort_index(axis=0)

            ts_multi_ix_df.dropna(axis=0, how="any", inplace=True)
            self.base_net_df = ts_multi_ix_df.loc[:,["Net_Demand", "Net_Generation"]]
            ################
            print(message_03)
            ################
            self.optimization_outputs["BASE"]["timeseries"] = ts_multi_ix_df

        if message_type == "REQ-EQ":
            ################
            print(message_06)
            ################
            costs = dict()
            ts_multi_ix = pd.MultiIndex.from_product([global_timeperiods, self.environ.list_of_active_ems], names=['time', 'ems'])
            ts_multi_ix_df = pd.DataFrame(index=ts_multi_ix, columns=self.UDI_events["BASE"]["EMS_1"].values.columns)
            ix = global_req_names.index(flex_req[0])

            for ems in self.environ.EMS:
                flex_req_act = flex_req[1][ems.agent_id]
                self.UDI_events[global_offer_names[ix+1]] = dict()
                self.UDI_events[global_offer_names[ix+1]][ems.agent_id] = ems.post_UDI_event(type="REQ", flex_req=flex_req_act)
                df = self.UDI_events[global_offer_names[ix+1]][ems.agent_id].values
                self.optimization_outputs[global_offer_names[ix+1]]["costs"][ems.agent_id] = self.UDI_events[global_offer_names[ix+1]][ems.agent_id].costs
                ts_multi_ix_df = pd.concat([ts_multi_ix_df, df], axis = 0, levels=1).sort_index(axis=0)

            ts_multi_ix_df.dropna(axis=0, how="any", inplace=True)
            self.optimization_outputs[global_offer_names[ix+1]]["timeseries"] = ts_multi_ix_df

        if message_type == "REQ-RAN":
            print(message_05 + "RANDOM")
            costs = dict()
            ts_multi_ix = pd.MultiIndex.from_product([global_timeperiods, self.environ.list_of_active_ems], names=['time', 'ems'])
            ts_multi_ix_df = pd.DataFrame(index=ts_multi_ix, columns=self.UDI_events["BASE"]["EMS_1"].values.columns)
            ix = global_req_names.index(flex_req[0])

            for ems in self.environ.EMS:
                print("Act Agent:{}\n".format(ems.agent_id))
                flex_req_act = flex_req[1][ems.agent_id]
                self.UDI_events[global_offer_names[ix+1]] = dict()
                self.UDI_events[global_offer_names[ix+1]][ems.agent_id] = ems.post_UDI_event(type="REQ", flex_req=flex_req_act)
                df = self.UDI_events[global_offer_names[ix+1]][ems.agent_id].values
                self.optimization_outputs[global_offer_names[ix+1]]["costs"][ems.agent_id] = self.UDI_events[global_offer_names[ix+1]][ems.agent_id].costs
                ts_multi_ix_df = pd.concat([ts_multi_ix_df, df], axis = 0, levels=1).sort_index(axis=0)

            ts_multi_ix_df.dropna(axis=0, how="any", inplace=True)
            self.optimization_outputs[global_offer_names[ix+1]]["timeseries"] = ts_multi_ix_df

        if message_type == "DATA":
            print("TA sends post_device_message for DATA REQUEST")
            try:
                self.UDI_events["DATA"]
            except:
                self.UDI_events["DATA"] = {}
            for ems in self.environ.EMS:
                self.UDI_events["DATA"][ems.agent_id] = ems.post_UDI_event(type="DATA", flex_req=None)
                self.multi_ix_df = self.UDI_events["DATA"][ems.agent_id].values["timeseries"]
                self.parameter_ems[ems.agent_id] = self.UDI_events["DATA"][ems.agent_id].values["parameter"]

            print("Offers:{}".format(self.UDI_events["OFFERS"].keys()))
            return

    def post_prognosis(self, prognosis_type):
        ''' Sends Prognosis-Object to MA and concurrently asks for Flex-Requests, by calling MAs "post_flex_request()"-function.
            Prognosis-Object gets the sum of all agents purchased and sold energy as value input, as well as the prices and remunerations paid and received for those enery amounts.
        '''
        if prognosis_type == "BASE":
            self.prognosis["BASE"] = Prognosis(id=self.prognosis_cnt, prognosis_type="BASE")
            self.prognosis_cnt += 1
            buy_sum_df = pd.DataFrame(index=global_timeperiods)
            sell_sum_df = pd.DataFrame(index=global_timeperiods)

            if self.optimization_mode == "flex-split":
                for ems in self.environ.list_of_active_ems:
                    buy_df = self.UDI_events["BASE"][ems].values.loc[:,"Net_Demand"]
                    buy_df.reset_index(level=1, inplace=True, drop=True)
                    buy_sum_df[ems] = buy_df

                    sell_df = self.UDI_events["BASE"][ems].values.loc[:,"Net_Generation"]
                    sell_df.reset_index(level=1, inplace=True, drop=True)
                    sell_sum_df[ems] = sell_df

                buy_sum_df = buy_sum_df.sum(axis=1)
                buy_sum_df = buy_sum_df.sum(axis=0)
                self.prognosis["BASE"].values["Net_Demand"] = buy_sum_df
                sell_sum_df = sell_sum_df.sum(axis=1) #.sum(axis=0)
                sell_sum_df = sell_sum_df.sum(axis=0)
                self.prognosis["BASE"].values["Net_Generation"] = sell_sum_df

            if self.optimization_mode == "central":
                buy_sum_df = self.optimization_outputs["BASE"]["timeseries"].loc[:,"Net_Demand"]
                sell_sum_df = self.optimization_outputs["BASE"]["timeseries"].loc[:,"Net_Generation"]
                self.prognosis["BASE"].values["grid_demand"] = buy_sum_df.sum(axis=0, level="time")
                self.prognosis["BASE"].values["grid_supply"] = sell_sum_df.sum(axis=0, level="time")
            ################
            print(message_04)
            ################
            self.flex_requests = self.environ.MA.post_flex_request(prognosis=self.prognosis["BASE"], prognosis_type="BASE")
            return

    def calc_stats(self):
        base_costs = dict()

        for ems in self.environ.EMS:
            base_costs[ems.agent_id] = self.optimization_outputs["BASE"]["costs"][ems.agent_id]

        for offer in self.optimization_outputs:
            self.optimization_outputs[offer]["stats"] = dict()

    def post_flex_offer(self):
        ''' Calls TAs function "calc_flex_req_costs()" in order to come up with an flex_offer_price, and then posts this price to the MA'''
        # self.optimization_outputs
        flex_offer = FlexOffer()
        flex_offer.id = "FLEX-OFFERS"
        flex_offer.price = self.calc_stats()
        print(message_10)
        self.environ.MA.post_flex_order(flex_offer)
        self.flex_offer_cnt += 1
        return

    def flex_request_split(self):
        self.multi_ix_df = dict()
        for offer in self.UDI_events["OFFERS"].keys():
            self.optimization_outputs[offer] = dict()
            self.optimization_outputs[offer]["timeseries"] = dict()
            self.optimization_outputs[offer]["costs"] = dict()

        if self.flex_split_mode == "equal":
            equal_requests = dict()
            for flex_req in global_req_names:
                equal_requests[flex_req] = dict()
                for ems in self.environ.EMS:
                    total_request = self.flex_requests.values[flex_req].astype("float64")
                    equal_requests[flex_req][ems.agent_id] = total_request / float(len(self.environ.EMS))

            #print("Equal_requests:{}".format(equal_requests.keys()))
            for flex_req in equal_requests.items():
                self.post_device_message(message_type='REQ-EQ', flex_req=flex_req)
            print(message_09)

        if self.flex_split_mode == "ran-3":
            cnt = 0
            random_requests = dict()
            for flex_req in global_req_names:
                agent_split_reqs = dict()
                random_requests = dict()
                random_requests[flex_req] = dict()
                request = self.flex_requests.values[flex_req]

                for agent in self.environ.list_of_active_ems:
                    agent_split_reqs[agent] = []

                for val in request:
                    rands = []
                    for agent in self.environ.list_of_active_ems:
                        rands.append(round(random.uniform(0, val),3))
                    s = np.sum(rands)
                    splits = []
                    for ran, agent in zip(rands, agent_split_reqs):
                        split = round((ran/s*val),3)
                        agent_split_reqs[agent].append(split)

                for split, agent in zip(agent_split_reqs.items(), self.environ.list_of_active_ems):
                    random_requests[flex_req][agent] = pd.Series(agent_split_reqs[agent])
                    random_requests[flex_req][agent].fillna(value=0, inplace=True)

                for req in random_requests.items():
                    self.post_device_message(message_type='REQ-RAN', flex_req=req)
                    cnt += 1
            print(message_09)
        return

    def step(self):
        '''Actual Sequence of events that occur within one model step. TAs step function gets called upfront within the environments step function.'''
        if self.optimization_mode == "central":
            print("----------- Optimization Mode: CENTRAL -----------")
            # Get DEMAND, GENERATION and PARAMETER from EMS as UDI-EVENT
            print("1.CENTRAL: TA requests Data from EMS")
            self.post_device_message("DATA", flex_req=None)
            self.central_optimization("BASE")
            self.post_prognosis(prognosis_type="BASE")
            self.central_optimization("FLEX_REQ")
            self.post_flex_offer()

        elif self.optimization_mode == "flex-split":
            print("----------- Optimization Mode: FLEX-SPLIT -----------")
            self.post_device_message("BASE", flex_req=None)
            self.post_prognosis(prognosis_type="BASE")
            if self.flex_split_mode == "ran-3":
                costs_random_runs = dict()
                revs_random_runs = dict()
                self.flex_request_split()
                self.random_datasets["ran_1"] = dict()
                for offer in global_offer_names:
                    total_costs = 0
                    if offer != "BASE":
                        for ems in self.environ.EMS:
                            total_costs+=self.optimization_outputs[offer]["costs"][ems.agent_id]
                self.random_datasets["ran_1_costs"] = total_costs
                print(self.random_datasets["ran_1_costs"])
                self.random_datasets["ran_1_ts"] = self.optimization_outputs

                self.flex_request_split()
                self.random_datasets["ran_2"] = dict()
                for offer in global_offer_names:
                    total_costs = 0
                    if offer != "BASE":
                        for ems in self.environ.EMS:
                            total_costs+=self.optimization_outputs[offer]["costs"][ems.agent_id]
                self.random_datasets["ran_2_costs"] = total_costs
                print(self.random_datasets["ran_2_costs"])
                self.random_datasets["ran_2_ts"] = self.optimization_outputs

                self.flex_request_split()
                self.random_datasets["ran_3"] = dict()
                for offer in global_offer_names:
                    total_costs = 0
                    if offer != "BASE":
                        for ems in self.environ.EMS:
                            total_costs+=self.optimization_outputs[offer]["costs"][ems.agent_id]
                self.random_datasets["ran_3_costs"] = total_costs
                print(self.random_datasets["ran_3_costs"])
                self.random_datasets["ran_3_ts"] = self.optimization_outputs

                for key in self.random_datasets.keys():
                    if "costs" in key:
                        costs_random_runs[key] = self.random_datasets[key]
                for costs in costs_random_runs.items():
                    if costs[1] < 0:
                        revs_random_runs[costs[0]] = costs[1]
                    else:
                        revs_random_runs = None

                if revs_random_runs != None:
                    print("Revs of Runs:{}".format(costs_random_runs))
                    max_revs = min(revs_random_runs.items())
                    print("Run with max revs:{}\n".format(max_revs))

                    if max_revs == "ran_1_costs":
                        self.optimization_outputs = self.random_datasets["ran_1_ts"]
                    if max_revs == "ran_2_costs":
                        self.optimization_outputs = self.random_datasets["ran_2_ts"]
                    if max_revs == "ran_3_costs":
                        self.optimization_outputs = self.random_datasets["ran_3_ts"]
                    print(self.optimization_outputs.keys())
                else:
                    print("Costs of Runs:{}".format(costs_random_runs))
                    min_costs = {k for k,v in costs_random_runs.items() if v == min(costs_random_runs.values())}
                    print("Run with min costs:{}\n".format(min_costs))

                    if min_costs == "ran_1_costs":
                        self.optimization_outputs = self.random_datasets["ran_1_ts"]
                    if min_costs == "ran_2_costs":
                        self.optimization_outputs = self.random_datasets["ran_2_ts"]
                    if min_costs == "ran_3_costs":
                        self.optimization_outputs = self.random_datasets["ran_3_ts"]
            else:
                self.flex_request_split()
            self.calc_stats()
            self.post_flex_offer()
        else:
            print("Not recognized optimization mode: %s." % self.optimization_mode)
        return
#------------------------------------------------------------------------------ EMS ----------------------------------------------------------------------------------------#
class EMS(Agent):
    ''' Prosumer-type agents that has several (shiftable) consumer devices like photopholtaics, batteries, EV, etc. attached. Represented as an EM-System, instances of this class holds consumptiona and generation
        timeseries and device parameters which can be used to calculate (optimal) energy management schedules.

    Args:
        agent_id:   unique name of each EMS entity. gets automatically assigned within instantiation.
        environ:    every agent "knows" the environment he lives in. gets automatically assigned within instantiation.

    Attributes:
        ts:         holds TA timeseries data that gets specified within the input excel file. Can also be called via ems_ts[a[1]].
        param:      holds TA parameter data that gets specified within the input excel file. Can also be called via data["TA_param"].
        UDI_events: a dictionary with keys and items according to the respective UDI-events type that the TA receives from its EM-Systems.
                e.g. {"BASE": (EMS[0].UDIevent.type("BASE"), EMS[1].UDIevent.type("BASE"),..)}
                        => for every UDI-Event-Type there's one UDI-Event per agent
                        => UDI-Event-Objects are callable through: self.UDI_events[name of the UDI-Event][ems.agent_id]
                UDI-Events-Objects gets instaniated by the EM-Systems and gets stored within the TAs scope by calling TAs function "post_device_message()",
                which has the EM-System function "post_UDI_event()" encapsulated as a callback.
    self.costs: a dictionary that holds the costs output from the milp-optimization for each run
    '''
    #An agent with gen, battery and load profile
    def __init__(self, agent_id, environ, timeseries, parameter):
        super().__init__(agent_id, environ)
        self.timeseries = timeseries["ems"]
        self.UDI_events= dict()
        self.UDI_event_id = 0
        self.costs = dict()
        self.timeseries = timeseries["ems"]
        self.parameter = parameter["ems"][self.agent_id]
        self.flags = parameter["flags"]
        self.single_ix_df = None
        self.request_cnt = 1

    def post_UDI_event(self, type, flex_req):
        ''' Creates an UDI-Event-Object and writes the output of the optimization on it.'''
        id = self.UDI_event_id
        UDI_event = UDIevent(id)

        if type == "DATA":
            print("2.CENTRAL: {} sends UDI-EVENT for Data Request from TA".format(self.agent_id))
            UDI_event.type = "DATA"
            UDI_event.values["timeseries"] = self.timeseries["BASE"]
            UDI_event.values["parameter"] = self.parameter
            UDI_event.costs = 0
            self.UDI_events[type] = UDI_event
            self.UDI_event_id += 1
            self.base_net_df = None
            return UDI_event

        elif type == "BASE":
            print(message_02)
            single_ix_df = pd.DataFrame(self.timeseries["BASE"])
            self.single_ix_df = single_ix_df.loc[single_ix_df.index.get_level_values("ems") == self.agent_id]
            parameter = dict()
            parameter[self.agent_id] = self.parameter
            solver_output = solver(name="BASE",
                                    multi_ix_df=self.single_ix_df,
                                    parameter=parameter,
                                    flex_request=None,
                                    flags=self.flags,
                                    timeperiods = self.environ.timeperiods,
                                    type="BASE",
                                    mode="flex-split",
                                    active_ems=self.environ.list_of_active_ems,
                                    base_net = None)
            UDI_event.type = "BASE"
            UDI_event.values = solver_output[0]
            UDI_event.costs = solver_output[1]
            self.UDI_events[type] = UDI_event
            self.UDI_event_id += 1
            self.base_net_df = UDI_event.values.loc[:,["Net_Demand", "Net_Generation","Switch_BUY","Switch_SELL"]]
            return UDI_event

        elif type == "REQ":
            ################
            print(message_07)
            ################
            parameter = dict()
            parameter[self.agent_id] = self.parameter
            solver_output = solver(name="REQ_"+ str(self.request_cnt),
                                    multi_ix_df=self.single_ix_df,
                                    parameter=parameter,
                                    flex_request=flex_req,
                                    flags=self.flags,
                                    timeperiods = self.environ.timeperiods,
                                    type="REQ",
                                    mode="flex-split",
                                    active_ems=self.environ.list_of_active_ems,
                                    base_net = self.base_net_df)
            UDI_event.values = solver_output[0]
            UDI_event.type = "OFFER"
            UDI_event.costs = solver_output[1]
            self.UDI_events[type] = UDI_event
            self.UDI_event_id += 1
            self.request_cnt += 1
            ################
            print(message_08)
            ################
            return UDI_event
