from utils import Agent
from model.messages import *
from solver.battery_solver import battery_solver
from data_structures.message_types import Prognosis, FlexReq, FlexOffer, FlexOrder, UDIevent
from globals import *
from globals import global_last_request_costs
#from app import *
import random
import datetime as dt
import pandas as pd
import numpy as np


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
            solver_output = battery_solver(name="BASE",
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
            solver_output = battery_solver(name="REQ_"+ str(self.request_cnt),
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
