from typing import Callable, List, Optional, Tuple, Union
from datetime import timedelta
from math import sin

from pandas import DataFrame, date_range, Series, isna, isnull

from comopt.utils import Agent
from comopt.model.utils import initialize_df
from comopt.data_structures.commitments import DeviationCostCurve
from comopt.data_structures.message_types import Request
from comopt.data_structures.usef_message_types import (
    Prognosis,
    FlexRequest,
    FlexOffer,
    FlexOrder,
)
from random import uniform
from numpy import nan, nan_to_num, where, arange, around


class MarketAgent(Agent):
    """
    A market agent (MA) represents an external agent that has a need for flexibility (Flexibility Requesting Party
    such as an energy supplier or a network operator).
    """

    def __init__(
        self,
        name,
        environment,
        flex_trade_horizon: timedelta,
        balancing_opportunities: DataFrame,
        # deviation_prices: Union[Tuple[int], int],
        # prognosis_policy: Callable,
        prognosis_parameter: dict,
        # flexrequest_policy: Callable,
        flexrequest_parameter: dict,
        # sticking_factor: float,
        # deviation_multiplicator: float,
        # imbalance_market_costs: Series,
    ):
        """ Creates an instance of the Class MarketAgent. Inherits from the Class Agent """
        super().__init__(name, environment)

        commitment_data_columns = [
            "Imbalances",
            "Imbalance market price",
            "Imbalance market costs",
            "Prognosis values",
            "Prognosis costs",
            "Requested flexibility",
            "Realised flexibility",
            "Commited flexibility",
            "Deviated flexibility",
            "Flexibility costs",
            "Deviation prices",
            "Deviation revenues",
            "Remaining imbalances",
            "Remaining market costs",
            "Opportunity costs",
        ]
        self.commitment_data = initialize_df(
            commitment_data_columns, environment.start, environment.end, environment.resolution
        )

        self.commitment_data.loc[:, "Deviation prices"] = flexrequest_parameter["Deviation prices"]
        self.commitment_data.loc[:, "Imbalances"] = balancing_opportunities.loc[:, "Imbalance (in MW)"]
        self.commitment_data.loc[:, "Imbalance market price"] = balancing_opportunities.loc[:, "Price (in EUR/MWh)"]
        self.commitment_data.loc[:, "Imbalance market costs"] = self.commitment_data.loc[:, "Imbalances"] \
                                                                * self.commitment_data.loc[:, "Imbalance market price"]
        # self.commitment_data.loc[:, "Received flexibility"] = 0

        self.flex_trade_horizon = flex_trade_horizon

        # self.balancing_opportunities = balancing_opportunities
        # self.deviation_prices = deviation_prices
        # self.deviation_prices_realised = [] #
        # self.sticking_factor = sticking_factor
        # self.prognosis_policy = prognosis_policy
        self.prognosis_parameter = prognosis_parameter
        # self.flexrequest_policy = flexrequest_policy
        self.flexrequest_parameter = flexrequest_parameter
        # self.deviation_multiplicator = deviation_multiplicator #
        # self.imbalance_market_costs = imbalance_market_costs

    def post_prognosis_request(self) -> Request:
        # prognosis_request_price = self.prognosis_policy()

        return Request(
            id=self.environment.plan_board.get_message_id(),
            requested_values=None,
            deviation_cost_curve=None,
            costs=None,
            start=self.environment.now,
            end=self.environment.now + self.environment.resolution,
            resolution=self.environment.resolution,
        )

    def post_flex_request(self, prognosis: Prognosis) -> FlexRequest:
        """Callback function to let the Market Agent create a FlexRequest based on a Prognosis and post it to the
        Trading Agent."""

        # Todo: rationalise the following
        # We assume that the balancing opportunities, which are put into the simulation as an exogenous variable,
        # already take into account the prognosis.

        # Get the Market Agent's unfulfilled balancing opportunities with positive value, which will become the
        # requested_power,
        flex_trade_window = (
            self.environment.now,
            self.environment.now + self.flex_trade_horizon,
        )

        requested_values = initialize_df(
            columns=["requested_power", "requested_flex", "requested_flex_imbalance_market_costs"],
            start=flex_trade_window[0],
            end=flex_trade_window[1],
            resolution=self.environment.resolution,
        )

        if uniform(0, 0.99) >= self.flexrequest_parameter["Sticking factor"]:

            print("\n----------------MA: POST FLEX REQUEST---------------------")

            original_commitment_opportunities = self.commitment_data.loc[
                flex_trade_window[0] : flex_trade_window[1]
                - self.environment.resolution,
                "Imbalances",
            ].values

            already_bought_commitment = around(self.commitment_data.loc[
                flex_trade_window[0] : flex_trade_window[1]
                - self.environment.resolution,
                "Commited flexibility",
            ].values.astype("float64"),3)

            remaining_commitment_opportunities = [
                opportunity - commitment if not isna(commitment) else opportunity
                for opportunity, commitment in zip(
                    original_commitment_opportunities, already_bought_commitment
                )
            ]
            remaining_commitment_opportunities = [
                nan if opportunity == 0 else opportunity
                for opportunity in remaining_commitment_opportunities
            ]

            requested_values["Requested flexibility"] = remaining_commitment_opportunities

            requested_values["Requested power"] = prognosis.commitment.constants.loc[
                                                        flex_trade_window[0] : flex_trade_window[1]- self.environment.resolution] \
                                                            + remaining_commitment_opportunities

            # Get market costs for flexibility for the acutal horizon
            requested_values["Requested costs"] = self.commitment_data.loc[
                                                            flex_trade_window[0] : flex_trade_window[1] - self.environment.resolution,
                                                            "Imbalance market costs"]

            # Only add market costs to reservation price for timesteps where requested flexibility is not nan
            self.flexrequest_parameter["Reservation price"] = 0
            for enum, val in enumerate(requested_values["Requested flexibility"]):
                if val != nan:
                    self.flexrequest_parameter["Reservation price"] += requested_values["Requested costs"].iloc[enum]

            print("\n MA: Reservation price: {}".format(self.flexrequest_parameter["Reservation price"]))
            print("\nMA: Already bought commitment: {}".format(already_bought_commitment))
            print("MA: Remaining commitment opportunities: {}".format(remaining_commitment_opportunities))
            print("\nMA: Requested Power values: {}".format(requested_values["Requested power"]))
            print("\nMA: Requested Flex values: {}\n".format(requested_values["Requested flexibility"]))
            print("\nMA: Requested Cost values: {}\n".format(requested_values["Requested costs"]))

        else: # TODO: Fix sticking
            requested_values["Requested power"] = prognosis.commitment.constants

            requested_values["Requested flexibility"] = nan

            print("----------------MA: STICKING ---------------------\n")
            print("MA: Request sticking to prognosis values: {}\n".format(prognosis.commitment.constants))

        # Store requested flexibility in MA commitment data
        for val, index in zip(requested_values["Requested flexibility"], requested_values["Requested power"].index):
            if not isnull(val):
                self.commitment_data.loc[index, "Requested flexibility"] = val

        return FlexRequest(
            id=self.environment.plan_board.get_message_id(),
            requested_values=round(requested_values["Requested power"],2),
            requested_flexibility=round(requested_values["Requested flexibility"],2),
            costs=round(self.flexrequest_parameter["Reservation price"] - self.flexrequest_parameter["Markup"] ,2),
            deviation_cost_curve=DeviationCostCurve(
                gradient=(
                    self.commitment_data.loc[self.environment.now, "Deviation prices"] * -1,
                    self.commitment_data.loc[self.environment.now, "Deviation prices"],
                ),
                flow_unit_multiplier=self.environment.flow_unit_multiplier,
            ),
            prognosis=prognosis,
        )

    def get_prognosis(self, prognosis) -> Prognosis:
        """Callback function to let the Market Agent get a Prognosis."""

        return prognosis

    def get_flex_offer(self, flex_offer: FlexOffer, order: bool = False) -> FlexOffer:
        """Callback function to let the Market Agent get a FlexOffer. Also the reservation price for the negotiation gets stored here."""

        if order == False:

            start = flex_offer.offered_values.index[0]
            end = flex_offer.offered_values.index[-1]

            # Assign MAs reservation price for flexibility negotiationabs
            self.flexrequest_parameter["Reservation price"] = sum(
                nan_to_num(abs(flex_offer.offered_flexibility)) * self.commitment_data.loc[start : end, "Imbalance market price"]

            )

        return flex_offer

    def post_flex_order(self, flex_offer: FlexOffer) -> Optional[FlexOrder]:
        """Callback function to let the Market Agent create a FlexOrder based on a FlexOffer and post it to the Trading
        Agent. Also the commited and realised values gets stored at this point."""

        flex_order = FlexOrder(
            id=self.environment.plan_board.get_message_id(), flex_offer=flex_offer
        )

        flexibility = flex_offer.offered_flexibility

        # Store commited flex for each step of actual horizon only if not nan.
        for index, row in flexibility.iteritems():

            if not isnull(flexibility.loc[index]):

                self.commitment_data.loc[index, "Commited flexibility"] = flexibility.loc[index]
                self.commitment_data.loc[flex_offer.start, "Realised flexibility"] = \
                    self.commitment_data.loc[flex_offer.start, "Commited flexibility"]


        if self.commitment_data.loc[flex_offer.start, "Realised flexibility"] > self.commitment_data.loc[flex_offer.start, "Imbalances"]:
            self.commitment_data.loc[flex_offer.start, "Deviated flexibility"] = \
                self.commitment_data.loc[flex_offer.start, "Realised flexibility"] - self.commitment_data.loc[flex_offer.start, "Imbalances"]

        elif self.commitment_data.loc[flex_offer.start, "Realised flexibility"] < self.commitment_data.loc[flex_offer.start, "Imbalances"]:
            self.commitment_data.loc[flex_offer.start, "Deviated flexibility"] = \
                self.commitment_data.loc[flex_offer.start, "Imbalances"] - self.commitment_data.loc[flex_offer.start, "Realised flexibility"]

        print("MA: Commited Flex: {} \n".format(self.commitment_data["Commited flexibility"]))
        print("MA: Realised Flex: {} \n".format(self.commitment_data["Realised flexibility"]))
        print("MA: Deviated Flex: {} \n".format(self.commitment_data["Deviated flexibility"]))
        print("MA: Requested Flex: {} \n".format(self.commitment_data["Requested flexibility"]))
        print("MA: Imbalances: {} \n".format(self.commitment_data["Imbalances"]))

        return flex_order

    def store_sold_power(self):

        # Update commitments due to realised power by each EMS
        # sold_power_in_step = 0
        # for ems in self.environment.ems_agents:
        #     sold_power_in_step += ems.realised_power.loc[self.environment.now, ]
        # self.commitment_data.loc[self.environment.now, "sold_power"] = sold_power_in_step
        # self.commitment_data.loc[self.environment.now, "power_revenues"] = (
        #     sold_power_in_step * self.retail_price
        # )
        return

    def step(self):
        return
