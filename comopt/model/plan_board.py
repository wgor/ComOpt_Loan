from typing import List
from datetime import datetime, timedelta

from comopt.data_structures.message_types import Request
from comopt.model.utils import initialize_df


class PlanBoard:
    """A plan board hands out message identifiers and is used to store all messages."""

    def __init__(self, start: datetime, end: datetime, resolution: timedelta):
        self.message_id = 1
        self.prognosis_negotiation_log_1 = None
        self.prognosis_negotiation_log_2 = None
        self.flexrequest_negotiation_log_1 = None
        self.flexrequest_negotiation_log_2 = None

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

    def create_message_logs(self, start: datetime, end: datetime, resolution: timedelta, environment):
        self.message_logs = dict()
        ems_names = [environment.ems_agents[x].name for x, ems in enumerate(environment.ems_agents)]
        ems_columns = ["DeviceMessage", "UdiEvent"]
        columns = ["Prognosis Request", "Prognosis", "FlexRequest", "FlexOffer", "FlexOrder"]
        periods = int(((end-start))/resolution)

        self.message_logs[next] = dict()
        self.message_logs[next]["TA"] = initialize_df(columns=columns, start=start, end=end, resolution=resolution)
        self.message_logs[next]["MA"] = initialize_df(columns=columns, start=start, end=end, resolution=resolution)
        self.message_logs[next]["EMS"] = {ems:initialize_df(columns=ems_columns, start=start, end=end, resolution=resolution) for ems in ems_names}


    # def store_negotiation_results(self, negotiation_results=None, key: datetime):
    #     for key in keys:
    #         if type(message) is Request:
    #             self.message_log[key].loc[message.start, "Prognosis Request"] = "ID " + str(message.id), message
    #         else:
    #             self.message_log[key].loc[message.start, message.__class__.__name__] = "ID " + str(message.id), message
