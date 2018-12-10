from typing import Callable, Dict, Union
from datetime import datetime, timedelta
from time import time

from pandas import DataFrame, Series
from comopt.model.utils import create_negotiation_log, initialize_index
from comopt.model.market_agent import MarketAgent
from comopt.model.plan_board import PlanBoard
from comopt.model.trading_agent import TradingAgent
from comopt.model.ems import EMS


class Environment:
    """ Model environment class.
        Within an environment agent instances of various types (e.g. Market-, Trading-, EMS-Agents) get created and stored,
        the simulation gets proceeded stepwise and the simulation steps get tracked.
    Args:
        input_data: a dictionary that provides timeseries and parameter values for the simulation.
        name: parameter to specify an environment by a given name.
    Attributes:
        execution_time: a timedelta expressing the time the simulation took to complete
        start: starting datetime of the simulation
        end: ending datetime of the simulation
        now: "current" datetime while the simulation is running
    """

    def __init__(
        self,
        name: str,
        start: datetime,
        end: datetime,
        resolution: timedelta,
        input_data: Dict[str, Union[DataFrame, Series, timedelta, bool, dict, Callable]],
    ):
        """Create simulation environment."""
        self.name = name

        # Set up time
        self.execution_time = None
        self.start = start
        self.end = end
        self.resolution = resolution
        self.now = start
        self.max_horizon = None
        self.simulation_runtime_index = initialize_index(start, end, resolution)
        self.step_now = 1
        self.total_steps = (
            end - start - max(input_data["TA horizon"], input_data["MA horizon"])
        ) / resolution
        self.flow_unit_multiplier = resolution.seconds / 3600  # TODO: Replace usage of this attribute with self.resolution
        # self.commitment_snapshots = commitment_snapshots(start=start, end=end, ta_horizon=input_data["TA horizon"], ma_horizon=input_data["MA horizon"])

        # Set up agents
        num_ems = len(input_data["EMS constraints"])
        self.ems_agents = [
            EMS(
                name="EMS %s" % (a + 1),
                environment=self,
                devices=input_data["Device constraints"][a],
                ems_constraints=input_data["EMS constraints"][a],
                ems_prices=input_data["EMS prices"][a],
            )
            for a in range(num_ems)
        ]
        self.market_agent = MarketAgent(
            name="Market agent",
            environment=self,
            flex_trade_horizon=input_data["MA horizon"],
            retail_price=10,
            balancing_opportunities=input_data["Balancing opportunities"],
            deviation_prices=input_data["MA deviation prices"],
            prognosis_policy=input_data["MA prognosis policy"],
            prognosis_parameter=input_data["MA prognosis parameter"],
            flexrequest_policy=input_data["MA flexrequest policy"],
            flexrequest_parameter=input_data["MA flexrequest parameter"],
            sticking_factor=input_data["MA flexrequest parameter"]["Sticking factor"],
            deviation_multiplicator=input_data["MA deviation multiplicator"],
            imbalance_market_costs=input_data["MA imbalance market costs"],
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
            flexrequest_rounds=input_data["Flexrequest rounds"],
            flexrequest_parameter=input_data["TA flexrequest parameter"],
            flexrequest_learning_parameter=input_data["Q parameter flexrequest"],
        )
        # Set up plan board
        self.plan_board = PlanBoard(start=start, end=end, resolution=resolution)
        # Create message log for each time period
        self.plan_board.create_message_logs(
            start=start, end=end, resolution=resolution, environment=self
        )

        # Set up prognosis negotiation log 1
        self.plan_board.prognosis_negotiation_log_1 = create_negotiation_log(
            start=self.start,
            end=self.end
            - self.resolution
            - max(
                self.market_agent.flex_trade_horizon,
                self.trading_agent.prognosis_horizon,
            ),
            resolution=self.resolution,
            rounds_total=input_data["Prognosis rounds"],
        )

        # Set up prognosis negotiation log 2
        self.plan_board.prognosis_negotiation_log_2 = create_negotiation_log(
            start=self.start,
            end=self.end
            - self.resolution
            - max(
                self.market_agent.flex_trade_horizon,
                self.trading_agent.prognosis_horizon,
            ),
            resolution=self.resolution,
            rounds_total=input_data["Prognosis rounds"],
        )

        # Set up flexrequest negotiation log 1
        self.plan_board.flexrequest_negotiation_log_1 = create_negotiation_log(
            start=self.start,
            end=self.end
            - self.resolution
            - max(
                self.market_agent.flex_trade_horizon,
                self.trading_agent.prognosis_horizon,
            ),
            resolution=self.resolution,
            rounds_total=input_data["Flexrequest rounds"],
        )

        # Set up flexrequest negotiation log 2
        self.plan_board.flexrequest_negotiation_log_2 = create_negotiation_log(
            start=self.start,
            end=self.end
            - self.resolution
            - max(
                self.market_agent.flex_trade_horizon,
                self.trading_agent.prognosis_horizon,
            ),
            resolution=self.resolution,
            rounds_total=input_data["Flexrequest rounds"],
        )

    def run_model(self):
        """Run the model until the end condition is reached."""
        start_time = time()
        self.max_horizon = max(
            self.market_agent.flex_trade_horizon, self.trading_agent.prognosis_horizon
        )

        last_step_due_to_agent_horizons = self.end - max(
            self.market_agent.flex_trade_horizon, self.trading_agent.prognosis_horizon
        )
        print("SIMULATION RUNTIME END: {}".format(last_step_due_to_agent_horizons))
        if last_step_due_to_agent_horizons < self.now:
            raise Exception(
                "Increase your simulation period or decrease your agent horizons."
            )

        while self.now <= last_step_due_to_agent_horizons:
            # print("Simulation progress: %s" % self.now)
            if self.now.hour == 0 and self.now.minute == 0:
                print("Simulation progress: day %s" % self.now.day)
            self.step()
        self.execution_time = timedelta(seconds=time() - start_time)

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
