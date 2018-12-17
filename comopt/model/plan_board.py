from typing import List
from datetime import datetime, timedelta

from comopt.data_structures.message_types import Request
from comopt.model.utils import create_negotiation_log, initialize_df


class PlanBoard:
    """A plan board hands out message identifiers and is used to store all messages."""

    def __init__(self, environment, prognosis_rounds: int, flex_rounds: int):
        self.message_id = 1

        max_agent_horizon = max(environment.market_agent.flex_trade_horizon, environment.trading_agent.prognosis_horizon)
        prognosis_negotiation_log = create_negotiation_log(
            start=environment.start,
            end=environment.end - environment.resolution - max_agent_horizon,
            resolution=environment.resolution,
            rounds_total=prognosis_rounds,
        )
        flex_negotiation_log = create_negotiation_log(
            start=environment.start,
            end=environment.end - environment.resolution - max_agent_horizon,
            resolution=environment.resolution,
            rounds_total=flex_rounds,
        )

        self.prognosis_negotiation_log_1 = prognosis_negotiation_log
        self.prognosis_negotiation_log_2 = prognosis_negotiation_log.copy()
        self.flexrequest_negotiation_log_1 = flex_negotiation_log
        self.flexrequest_negotiation_log_2 = flex_negotiation_log.copy()

    def get_message_id(self) -> int:
        id = self.message_id
        self.message_id += 1
        return id

    def store_message(self, timeperiod: datetime, message=None, keys: List[str] = None):
        return
        # for key in keys:
        #     if type(message) is Request:
        #         self.message_log[timeperiod][key].loc[message.start, "Prognosis Request"] = "ID " + str(message.id), message
        #     else:
        #         self.message_log[timeperiod][key].loc[message.start, message.__class__.__name__] = "ID " + str(message.id), message

    def create_message_logs(
        self, start: datetime, end: datetime, resolution: timedelta, environment
    ):
        self.message_logs = dict()
        ems_names = [
            environment.ems_agents[x].name
            for x, ems in enumerate(environment.ems_agents)
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

    # def store_negotiation_results(self, negotiation_results=None, key: datetime):
    #     for key in keys:
    #         if type(message) is Request:
    #             self.message_log[key].loc[message.start, "Prognosis Request"] = "ID " + str(message.id), message
    #         else:
    #             self.message_log[key].loc[message.start, message.__class__.__name__] = "ID " + str(message.id), message
