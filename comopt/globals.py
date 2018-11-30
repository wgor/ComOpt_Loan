from comopt.utils import data_import


# Data imported from excel  and used in app
excel_input_data = data_import("comopt/input_data.xlsx")
parameter_index = excel_input_data["EMS"].index.tolist()
timeperiods = excel_input_data["TA"].index.tolist()
parameter_profiles = excel_input_data["EMS"]
parameter_profiles.sample(1, axis=1)
EMS_table = None
TA_table = excel_input_data["TA"]
MA_table = excel_input_data["MA"]
prices_table = excel_input_data["Prices"]

# App callback variables
global_layer = ""
global_any_clicks = "No"
global_last_clicked = "ta"
global_agent_clicked_dict = dict()
global_last_tab = "SC_1"
global_active_ems = []
global_active_sc = ""
global_base_net_consumption = None
global_base_net_generation = None
global_base_net = None

# Model parameter sets
global_sc_names = [
    "SC_1",
    "SC_2",
    "SC_3",
    "SC_4",
    "SC_5",
    "SC_6",
    "SC_7",
    "SC_8",
    "SC_9",
]
global_ems_names = [
    "EMS_1",
    "EMS_2",
    "EMS_3",
    "EMS_4",
    "EMS_5",
    "EMS_6",
    "EMS_7",
    "EMS_8",
    "EMS_9",
]
global_offer_names = ["BASE", "OFFER_1", "OFFER_2", "OFFER_3", "OFFER_4", "OFFER_5"]
global_req_names = ["REQ_1", "REQ_2", "REQ_3", "REQ_4", "REQ_5"]
global_avail_names = ["BASE_AVAIL", "AVAIL_1", "AVAIL_2", "AVAIL_3", "AVAIL_4"]
global_timeperiods = list(range(1, 25))
global_SOC_timeperiods = list(range(0, 25))

## Main data passed to model from app
global_parameter_dict = dict()
global_timeseries_dict = dict()
"""
Dictionary keys and items:
global_timeseries_dict["ta"]["REQ_1","REQ_2","REQ_3","REQ_4","REQ_5"]
global_timeseries_dict["ma"]["REQ_1","REQ_2","REQ_3","REQ_4","REQ_5"]
global_timeseries_dict["ems"]=["BASE","OFFER_1","OFFER_2","OFFER_3","OFFER_4","OFFER_5"]
global_timeseries_dict["costs"]["ems"]=["BASE","OFFER_1","OFFER_2","OFFER_3","OFFER_4","OFFER_5"]
global_timeseries_dict["prices"]=["market_price","feed_in_tarif"]
global_timeseries_dict["messages"]=[]
"""
