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
from numpy import nan


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
        deviation_prices: Union[Tuple[int], int],
        prognosis_policy: Callable,
        prognosis_parameter: dict,
        flexrequest_policy: Callable,
        flexrequest_parameter: dict,
        sticking_factor: float,
        deviation_multiplicator: float,
        imbalance_market_costs: Series,
    ):
        """ Creates an instance of the Class MarketAgent. Inherits from the Class Agent """
        super().__init__(name, environment)
        columns = [
            "Prognosis values",
            "Prognosis costs",
            "Requested flexibility",
            "Commited flexibility",
            "Received flexibility",
            "Deviated flexibility",
            "Deviation prices",
            "Flexibility costs",
            "Deviation revenues",
            "Remaining imbalances",
            "Remaining market costs",
            "Imbalance market prices",
            "Opportunity costs",
        ]
        self.commitment_data = initialize_df(
            columns, environment.start, environment.end, environment.resolution
        )

        self.commitment_data.loc[:, "Deviation prices"] = deviation_prices
        self.commitment_data.loc[:, "Requested flexibility"] = balancing_opportunities.loc[:, "Imbalance (in MW)"]
        self.commitment_data.loc[:, "Imbalance market price"] = balancing_opportunities.loc[:, "Price (in EUR/MWh)"]
        self.commitment_data.loc[:, "Remaining market costs"] = imbalance_market_costs
        # self.commitment_data.loc[:, "Received flexibility"] = 0

        self.flex_trade_horizon = flex_trade_horizon

        self.balancing_opportunities = balancing_opportunities
        self.deviation_prices = deviation_prices
        self.deviation_prices_realised = [] #
        self.sticking_factor = sticking_factor
        self.prognosis_policy = prognosis_policy
        self.prognosis_parameter = prognosis_parameter
        self.flexrequest_policy = flexrequest_policy
        self.flexrequest_parameter = flexrequest_parameter
        self.deviation_multiplicator = deviation_multiplicator #
        self.imbalance_market_costs = imbalance_market_costs

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

        if uniform(0, 0.99) >= self.sticking_factor:

            print("\n----------------MA: POST FLEX REQUEST---------------------")

            original_commitment_opportunities = self.balancing_opportunities.loc[
                flex_trade_window[0] : flex_trade_window[1]
                - self.environment.resolution,
                "Imbalance (in MW)",
            ].values

            already_bought_commitment = self.commitment_data.loc[
                flex_trade_window[0] : flex_trade_window[1]
                - self.environment.resolution,
                "Commited flexibility",
            ].values

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

            requested_values["requested_flexibility"] = remaining_commitment_opportunities

            requested_values["requested_flex_imbalance_market_costs"] = self.imbalance_market_costs.loc[
                                                                        flex_trade_window[0] : flex_trade_window[1] - self.environment.resolution] \


            # prognosis.commitment.constants.loc[
            # flex_trade_window[0] : flex_trade_window[1] - self.environment.resolution] + remaining_commitment_opportunities
            print("Prognosis power values \n" + str(prognosis.commitment.constants))

            requested_values["requested_power"] = (
                prognosis.commitment.constants.loc[
                    flex_trade_window[0] : flex_trade_window[1]
                    - self.environment.resolution
                ]
                + remaining_commitment_opportunities
            )

            print("\nMA: Already bought commitment: {}".format(already_bought_commitment))
            print("MA: Remaining commitment opportunities: {}".format(remaining_commitment_opportunities))
            print("\nMA: Requested Power values: {}".format(requested_values["requested_power"]))
            print("\nMA: Requested Flex values: {}\n".format(requested_values["requested_flexibility"]))

        else: # TODO: Fix sticking
            requested_power["requested_power"] = prognosis.commitment.constants

            print("----------------MA: STICKING ---------------------\n")
            print("MA: Request sticking to prognosis values: {}\n".format(prognosis.commitment.constants))

        # Assign MAs reservation price for flexibility negotiationabs
        self.flexrequest_parameter["Reservation price"] = sum(
            self.imbalance_market_costs.loc[
            flex_trade_window[0] : flex_trade_window[1]
            - self.environment.resolution
            ]
        )

        # Store requested flexibility in MA commitment data
        self.commitment_data.loc[flex_trade_window[0] : flex_trade_window[1] - self.environment.resolution, \
                                 "Requested flexibility"] \
                                = requested_values["requested_flexibility"]

        return FlexRequest(
            id=self.environment.plan_board.get_message_id(),
            requested_values=requested_values["requested_power"],
            requested_flexibility=requested_values["requested_flexibility"],
            costs=requested_values["requested_flex_imbalance_market_costs"],
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

    def get_flex_offer(self, flex_offer: FlexOffer) -> FlexOffer:
        """Callback function to let the Market Agent get a FlexOffer."""

        # if flex_offer is not None:
        #     idx = flex_offer.commitment.constants.index
        #     if (isnull(self.commitment_data.loc[self.environment.now, "Negotiated flexibility"]) == True):
        #         for row, val in enumerate(flex_offer.commitment.constants.loc[flex_offer.start : (flex_offer.end - flex_offer.resolution)]):
        #             self.commitment_data.loc[idx[row], "Negotiated flexibility"] = flex_offer.offered_flexibility.loc[idx[row]]

        # print("MA: Negotiated Flex: {} \n".format(self.commitment_data["Negotiated flexibility"]))

        return flex_offer

    def post_flex_order(self, flex_offer: FlexOffer) -> Optional[FlexOrder]:
        """Callback function to let the Market Agent create a FlexOrder based on a FlexOffer and post it to the Trading
        Agent."""

        flex_order = FlexOrder(
            id=self.environment.plan_board.get_message_id(), flex_offer=flex_offer
        )

        # Store commitments -> TODO: Factor out
        if flex_order is not None:
            idx = flex_order.ordered_power.index
            for row, val in enumerate(
                flex_offer.commitment.constants.loc[
                    flex_order.start : flex_order.start,
                ]
            ):
                if val != flex_offer.prognosis.commitment.constants[row]:

                    total_ems_flexibility = 0
                    for ems in self.environment.ems_agents:
                        total_ems_flexibility += ems.planned_flex_per_device.loc[
                            idx[row], :
                        ].sum(axis=0)

                    self.commitment_data.loc[
                        idx[row], "Received flexibility"
                    ] = total_ems_flexibility
                    self.commitment_data.loc[idx[row], "Remaining imbalances"] = (
                        self.balancing_opportunities.loc[idx[row], "Imbalance (in MW)"]
                        - total_ems_flexibility
                    )

                    print("MA: Total EMS Flexibility: {}\n".format(total_ems_flexibility))
                    print("MA: Remaining Imblances: {}\n".format(self.commitment_data.loc[idx[row], "Remaining imbalances"]))

            # print("MA: Bought Flex: {} \n".format(self.commitment_data["Received flexibility"]))
            self.commitment_data.loc[self.environment.now, "flex_costs"] = flex_order.costs

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

        # Store commitments
        # self.store_sold_power()
        # self.commitment_data.loc[:, "Deviation prices"]_realised.append(
        #     self.commitment_data.loc[:, "Deviation prices"][self.environment.now]
        # )
        # self.deviation_prices = self.deviation_prices * self.deviation_multiplicator
