import pandas as pd


class Prognosis:
    """
    Prognosis messages are used to communicate A-plans and D-prognoses between USEF participants.
    values: "array with multiple flex options", price: "int or arr", flex_req_id:"int", con_group:"int"
    """

    def __init__(self, id: "int" = 0, prognosis_type: "str" = ""):
        self.id = 0
        self.type = prognosis_type
        self.values = dict()
        self.costs = pd.Series()
        self.revs = pd.Series()
        self.con_group = 0
        return


class FlexReq:
    """
    FlexRequests messages are used by MarketAgents to request flexibility from TradingAgents
    """

    def __init__(self, id: str = "", values={}, price={}, con_group: "int" = 0):
        self.id = 0
        self.values = dict()
        self.price = dict()
        self.prognosis_id = 0
        self.con_group = 0
        return


class FlexOffer:
    """
    FlexOffers are used by TradingAgents to make MarketAgents an offer for providing flexibility.
    """

    def __init__(self):
        self.id = 0
        self.price = 0
        self.flex_req_id = 0
        self.con_group = 0
        return


class FlexOrder:
    """
    FlexOrders are used by MarketAgents to purchase flexibility from an TradingAgents based on a previous FlexOffers.
    """

    def __init__(self, id: "int", commit: "binary"):
        # FlexOrder with an id, commit indicates if offer got accepted (TRUE) or (REJECTED)
        self.id = 0
        self.commit = commit
        return


class UDIevent:
    """
    The UDI-Event element describes an energy consumption or production event performed by the EMS and initiated by
    the Trading Agent baseline: "nested list [[x0],[p0]]",
    alternatives: "[([x0],[p0]), [([x01],[p01]),...[([xn],[pn])]", costs
    """

    def __init__(self, id):
        self.id = 0
        self.type = 0
        self.values = 0
        self.costs = 0
        return
