from typing import List
from datetime import datetime, timedelta

from comopt.data_structures.message_types import Request
from comopt.model.utils import initialize_df
# from comopt.model.environment import Environment

from comopt.model.negotiation_utils import create_negotiation_data_log



class PlanBoard:
    """A plan board hands out message identifiers and is used to store all messages."""

    def __init__(self, start: datetime, end: datetime, resolution: timedelta, input_data: dict, environment):

        self.message_id = 1

        # Create message log for each time period
        self.message_log = self.create_message_log(
            start=start, end=end, resolution=resolution, environment=environment
        )

        # Set up prognosis negotiation log 1
        self.prognosis_negotiation_log_1 = create_negotiation_data_log(
            description="Prognosis init",
            start=start,
            end=end - resolution - environment.max_horizon,
            resolution=resolution,
            rounds_total=input_data["Prognosis rounds"],
        )

        # Set up flexrequest negotiation log 1
        self.flexrequest_negotiation_logs = dict()

        # = create_negotiation_data_log(
        #     type="adverse flexrequest",
        #     start=start,
        #     end=end - resolution - environment.max_horizon,
        #     resolution=resolution,
        #     rounds_total=input_data["Flexrequest rounds"][0],
        # )

        # Set up flexrequest negotiation log 2
        # self.flexrequest_negotiation_log_2 = create_negotiation_data_log(
        #     type="plain flexrequest",
        #     start=start,
        #     end=end - resolution - environment.max_horizon,
        #     resolution=resolution,
        #     rounds_total=input_data["Flexrequest rounds"][1]
        # )

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


    def create_message_log(
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
