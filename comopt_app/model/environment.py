import numpy as np

from comopt_app.model.market_agent import *
from comopt_app.model.trading_agent import *
from comopt_app.model.ems import *
from comopt_app.globals import *


class Environment():
    """ Model environment class.
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
    def __init__(self, timeseries, parameter, active_ems, scenario, timeperiods, seed=None):
        ''' Creates and stores environment instances.'''

        self.running = True
        self.steps = 0
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
