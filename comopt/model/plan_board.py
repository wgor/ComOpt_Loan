from typing import List, Union
from datetime import datetime, timedelta, date
from pandas import DataFrame, MultiIndex, date_range
from numpy import linspace
from copy import deepcopy
from collections import OrderedDict

from comopt.data_structures.message_types import Request
from comopt.model.utils import initialize_df
# from comopt.model.environment import Environment

class PlanBoard:
    """A plan board hands out message identifiers and is used to store all messages."""

    def __init__(self,
                 start: datetime,
                 end: datetime,
                 resolution: timedelta,
                 input_data: dict,
                 environment):

        # Counter variable for message ids
        self.message_id = 1
        self.input_data = input_data

        print(input_data["TA flexrequest parameter"]["Policy"].__name__)

        # Create message log with indices over model simulation runtime
        self.message_log = self.create_message_log(
            start=start,
            end=end,
            resolution=resolution,
            ems_agents=environment.ems_agents
        )

        # Set up prognosis negotiation log 1
        self.prognosis_negotiations_log = self.create_negotiation_data_log(
            start=start,
            end=end - resolution - environment.max_horizon,
            resolution=resolution,
            rounds_total=input_data["TA prognosis parameter"]["Negotiation rounds"],
        )

        # Set up prognosis negotiation log 1
        self.flexrequest_negotiations_log = self.create_negotiation_data_log(
            start=start,
            end=end - resolution - environment.max_horizon,
            resolution=resolution,
            rounds_total=input_data["TA flexrequest parameter"]["Negotiation rounds"],
        )

        self.prognosis_adaptive_strategy_data_log = self.create_adaptive_strategy_data_log(
            description="Prognosis",
            ta_parameter=input_data["TA prognosis parameter"],
            total_steps=environment.total_steps
            )

        self.flexrequest_adaptive_strategy_data_log = self.create_adaptive_strategy_data_log(
            description="Flexrequest",
            ta_parameter=input_data["TA prognosis parameter"],
            total_steps=environment.total_steps
            )

# -------------------------------------------------- Data logs --------------------------------------------------#

    def create_negotiation_data_log(
        self,
        start: Union[date, datetime],
        end: Union[date, datetime],
        resolution: timedelta,
        rounds_total: int,
    ) -> DataFrame:
        #TODO: change arguments to first_index,second_indexS

        """ Returns a multiindex dataframe with inidices (datetime, rounds) and columns for prices, bids, profits, etc. """

        print(rounds_total)
        logfile = DataFrame(
            index=MultiIndex.from_product(
                iterables=[
                    date_range(start, end, freq=resolution),
                    range(1, rounds_total + 1),
                ],
                names=["Datetime", "Round"],
            ),
            columns=[
                "Clearing price",
                "Cleared",
                "MA reservation price",
                "TA reservation price",
                "TA Counter reservation price",
                "MA markup",
                "TA markup",
                "TA Counter markup",
                "MA bid",
                "TA bid",
                "TA Counter offer",
                "MA profit",
                "TA profit",
            ],
        )
        return logfile


    def create_adaptive_strategy_data_log(
            self,
            description: str,
            ta_parameter: dict,
            total_steps: int):

        adaptive_strategy = ta_parameter["Policy"].__name__

        if "Simple" in adaptive_strategy:
            pass

        elif "Hill-climbing" in adaptive_strategy:
            pass

        elif "Q_learning" in adaptive_strategy:

            # Define timeperiods for storing snapshots
            self.snapshot_timesteps = linspace(
                1, total_steps, num=8, dtype="int", endpoint=True)

            if "Prognosis" in description:

                self.q_table_prognosis = DataFrame(
                    data=0,
                    index=range(1,ta_parameter["Negotiation rounds"] + 1),
                    columns=ta_parameter["Action function"](
                        action=None, markup=None, show_actions=True
                    ).keys(),
                )

                self.q_table_prognosis.index.name = "Rounds"
                self.action_table_prognosis = deepcopy(self.q_table_prognosis)
                self.snapshots_q_table_prognosis = OrderedDict()
                self.snapshots_action_table_prognosis = OrderedDict()

            elif "Flexrequest" in description:

                    self.q_table_flexrequest = DataFrame(
                        data=0,
                        index=range(1, ta_parameter["Negotiation rounds"] + 1),
                        columns=ta_parameter["Action function"](
                            action=None, markup=None, show_actions=True
                        ).keys(),
                    )

                    self.q_table_flexrequest.index.name = "Rounds"
                    self.action_table_flexrequest = deepcopy(self.q_table_flexrequest)
                    self.snapshots_q_table_flexrequest = OrderedDict()
                    self.snapshots_action_table_flexrequest = OrderedDict()


    def create_message_log(
        self,
        start: datetime,
        end: datetime,
        resolution: timedelta,
        ems_agents):

        self.message_logs = dict()
        ems_names = [
            ems_agents[x].name
            for x, ems in enumerate(ems_agents)
        ]
        ems_columns = ["DeviceMessage", "UdiEvent"]
        columns = [
            "Prognosis Request",
            "Prognosis",
            "FlexRequest",
            "FlexOffer",
            "FlexOrder",
        ]
        periods = int(((end - start)) / resolution)

        self.message_logs[next] = dict()
        self.message_logs[next]["TA"] = initialize_df(
            columns=columns, start=start, end=end, resolution=resolution
        )
        self.message_logs[next]["MA"] = initialize_df(
            columns=columns, start=start, end=end, resolution=resolution
        )
        self.message_logs[next]["EMS"] = {
            ems: initialize_df(
                columns=ems_columns, start=start, end=end, resolution=resolution
            )
            for ems in ems_names
        }

        return

    def get_message_id(self) -> int:
        id = self.message_id
        self.message_id += 1
        return id


    def store_message(self, timeperiod: datetime, message=None, keys: List[str] = None):
        # TODO: Fix the whole function
        # for key in keys:
        #     if type(message) is Request:
        #         self.message_log[timeperiod][key].loc[message.start, "Prognosis Request"] = "ID " + str(message.id), message
        #     else:
        #         self.message_log[timeperiod][key].loc[message.start, message.__class__.__name__] = "ID " + str(message.id), message

        return





    # def store_negotiation_results(self, negotiation_results=None, key: datetime):
    #     for key in keys:
    #         if type(message) is Request:
    #             self.message_log[key].loc[message.start, "Prognosis Request"] = "ID " + str(message.id), message
    #         else:
    #             self.message_log[key].loc[message.start, message.__class__.__name__] = "ID " + str(message.id), message
