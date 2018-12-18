from typing import Callable, Dict, List, Union
from datetime import datetime, timedelta

from pandas import DataFrame, Series
from comopt.model.utils import initialize_index
from comopt.model.negotiation_utils import create_negotiation_data_log
from comopt.model.market_agent import MarketAgent
from comopt.model.plan_board import PlanBoard
from comopt.model.trading_agent import TradingAgent
from comopt.model.ems import EMS


class Environment:
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

    def __init__(
        self,
        name: str,
        start: datetime,
        end: datetime,
        resolution: timedelta,
        ems_names: List[str],
        input_data: Dict[str, Union[DataFrame, Series, timedelta, bool, Callable]],
    ):
        """Create simulation environment."""
        self.name = name
        self.logfile = input_data["Logfile"]
        # Set up time
        self.start = start
        self.end = end
        self.resolution = resolution
        self.now = start
        self.max_horizon = max(
            input_data["TA horizon"], input_data["MA horizon"]
        )

        self.simulation_runtime_index = initialize_index(start, end, resolution)
        self.step_now = 1
        self.total_steps = (
            end - start - self.max_horizon
        ) / resolution
        self.flow_unit_multiplier = input_data["Flow unit multiplier"]
        # self.commitment_snapshots = commitment_snapshots(start=start, end=end, ta_horizon=input_data["TA horizon"], ma_horizon=input_data["MA horizon"])

        # Set up agents
        ems_agents = []
        for a, ems_name in enumerate(ems_names):
            ems_agents.append(
                EMS(
                    name=ems_name,
                    environment=self,
                    devices=input_data["Devices"][a],
                    ems_constraints=input_data["EMS constraints"][a],
                    ems_prices=input_data["EMS prices"][a],
                    flex_price=input_data["EMS prices"][a][2]
                )
            )
        self.ems_agents = ems_agents
        self.market_agent = MarketAgent(
            name="Market agent",
            environment=self,
            flex_trade_horizon=input_data["MA horizon"],
            balancing_opportunities=input_data["Balancing opportunities"],
            deviation_prices=input_data["MA Deviation Prices"],
            prognosis_policy=input_data["MA prognosis policy"],
            prognosis_parameter=input_data["MA prognosis parameter"],
            flexrequest_policy=input_data["MA flexrequest policy"],
            flexrequest_parameter=input_data["MA flexrequest parameter"],
            sticking_factor=input_data["MA flexrequest parameter"]["Sticking factor"],
            deviation_multiplicator=input_data["MA Deviation Multiplicator"],
            imbalance_market_costs=input_data["MA imbalance_market_costs"],
        )
        self.trading_agent = TradingAgent(
            name="Trading agent",
            environment=self,
            market_agent=self.market_agent,
            ems_agents=self.ems_agents,
            prognosis_horizon=input_data["TA horizon"],
            reprognosis_period=timedelta(hours=6),
            central_optimization=input_data["Central optimization"],
            prognosis_policy=input_data["TA prognosis policy"],
            prognosis_rounds=input_data["Prognosis rounds"],
            prognosis_parameter=input_data["TA prognosis parameter"],
            prognosis_learning_parameter=input_data["Q parameter prognosis"],
            flexrequest_policy=input_data["TA flexrequest policy"],
            flexrequest_parameter=input_data["TA flexrequest parameter"],
            flexrequest_learning_parameter=input_data["Q parameter flexrequest"],
            flexrequest_rounds=input_data["Flexrequest rounds"],
        )
        # Set up planboard
        self.plan_board = PlanBoard(start=start, end=end, resolution=resolution,
                                   input_data=input_data, environment=self)

    def run_model(self):
        """Run the model until the end condition is reached."""

        last_step_due_to_agent_horizons = self.end - self.max_horizon

        self.logfile.write("SIMULATION RUNTIME END: {}\n \n".format(last_step_due_to_agent_horizons))

        if last_step_due_to_agent_horizons < self.now:
            raise Exception(
                "Increase your simulation period or decrease your agent horizons."
            )

        while self.now <= last_step_due_to_agent_horizons:
            # print("Simulation progress: %s" % self.now)
            # if self.now.minute == 45:
            #     break
            if self.now.hour == 0 and self.now.minute == 0:
                self.logfile.write("Simulation progress: day %s" % self.now.day)
            self.step()

        Prefix = "Prog "
        self.logfile.write("\nDEVICE: Prognosis data:\n \n{}".format(self.ems_agents[0].device_data.loc[
                                                                :, [str(Prefix + "power"), str(Prefix + "flexibility"), \
                                                                                  str(Prefix + "contract costs"), \
                                                                                  ]], '.2f'))

        self.logfile.write("\nEMS: Prognosis data:\n \n{}".format(self.ems_agents[0].ems_data.loc[:, ["Req power", str(Prefix + "power"), \
                                                                            "Req flexibility", str(Prefix + "flexibility"), \
                                                                            str(Prefix + "contract costs"), str(Prefix + "dev costs"), \
                                                                            str(Prefix + "flex costs"), str(Prefix + "commitment costs")]],'.2f'))
        Prefix = "Plan "
        self.logfile.write("\nDEVICE: Planned data:\n \n{}".format(self.ems_agents[0].device_data.loc[:, [str(Prefix + "power"), str(Prefix + "flexibility"), \
                                                                                  str(Prefix + "contract costs"), \
                                                                                  ]],'.2f'))

        self.logfile.write("\nEMS: Planned data:\n \n{}".format(self.ems_agents[0].ems_data.loc[:, ["Req power", str(Prefix + "power"), \
                                                                    "Req flexibility", str(Prefix + "flexibility"), \
                                                                    str(Prefix + "contract costs"), str(Prefix + "dev costs"), \
                                                                    str(Prefix + "flex costs"), str(Prefix + "commitment costs")]],'.2f'))

        Prefix = "Real "
        self.logfile.write("\nDEVICE: Realised data:\n \n \n{}".format(self.ems_agents[0].device_data.loc[:, [str(Prefix + "power"), str(Prefix + "flexibility"), \
                                                                          str(Prefix + "contract costs") \
                                                                          ]],'.2f'))

        self.logfile.write("\nEMS: Realised data:\n \n{}".format(self.ems_agents[0].ems_data.loc[:, ["Req power", str(Prefix + "power"), \
                                                                    "Req flexibility", str(Prefix + "flexibility"), \
                                                                    str(Prefix + "contract costs"), \
                                                                    str(Prefix + "flex costs"), str(Prefix + "commitment costs")]],'.2f'))


        self.logfile.close()



    def step(self):
        """Proceed the simulation by one time step with the given resolution."""

        # Let the Trading Agent move (to create commitments)
        self.trading_agent.step()

        # Let each EMS move (to store their own commitments)
        for ems in self.ems_agents:
            ems.step()

        # Let the Market Agent move (to store its own commitments)
        self.market_agent.step()

        # Update simulation time
        self.now += self.resolution
        self.step_now += 1
