from utils import Agent
from model.messages import *
from data_structures.message_types import Prognosis, FlexReq, FlexOffer, FlexOrder, UDIevent
from globals import *

import random
import datetime as dt
import pandas as pd
import numpy as np

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
