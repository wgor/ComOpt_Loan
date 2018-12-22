from typing import Callable, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from numpy import nan
from pandas import DataFrame, Series, concat, isnull
from copy import deepcopy

from comopt.data_structures.commitments import (
    DeviationCostCurve,
    PiecewiseConstantProfileCommitment as Commitment,
)
from comopt.model.ems import EMS
from comopt.model.flex_split_methods import (
    equal_flex_split_requested,
    implement_your_own_flex_split_method_here,
)
from comopt.model.market_agent import MarketAgent
from comopt.model.opportunity_costs import determine_opportunity_costs_model_a
from comopt.model.utils import (
    initialize_df,
    initialize_index,
    initialize_series,
    create_multi_index_log,
    sort_out_already_commited_values
)
from comopt.model.negotiation_utils import (
    start_negotiation,
    update_adaptive_strategy_data
)

#TODO: Add create_adverse_and_plain_offers -> didnt find the bug, "Error: Can't import initialize_series"
from comopt.utils import Agent, create_adverse_and_plain_offers
from comopt.data_structures.utils import select_applicable
from comopt.data_structures.usef_message_types import (
    Prognosis,
    FlexRequest,
    FlexOffer,
    FlexOrder,
    UdiEvent,
    DeviceMessage,
)


class TradingAgent(Agent):
    """
    An Aggregator-like entity who acts as an intermediate agent between a market agent and the EMS agents of Prosumers.
    Collects, aggregates and trades flexibility.
    """

    def __init__(
        self,
        name,
        market_agent: MarketAgent,
        ems_agents: List[EMS],
        environment,
        flex_trade_horizon: timedelta,
        reprognosis_period: timedelta,
        # prognosis_policy: Callable,
        prognosis_parameter: dict,
        # prognosis_rounds: int,
        # prognosis_learning_parameter: dict,
        # flexrequest_policy: Callable,
        flexrequest_parameter: dict,
        # flexrequest_rounds: int,
        # flexrequest_learning_parameter: dict,
        central_optimization: bool = False,
    ):
        """ Creates an instance of the Class TradingAgent. Inherits from the Class Agent."""
        super().__init__(name, environment)

        self.market_agent = market_agent
        self.ems_agents = ems_agents

        columns_aggregated_ems_data = [
                  "Activated EMS", "Requested power", "Requested flexibility", \
                  "Prog power", "Plan power", "Realised power", "Deviated power",\
                  "Prog flexibility", "Plan flexibility", "Realised flexibility", "Deviated flexibility", \
                  ]

        self.ems_data = initialize_df(
            columns_aggregated_ems_data, environment.start, environment.end, environment.resolution
        )

        columns_commitment_data = [
                  "Requested power", "Requested flexibility",
                  "Commited power", "Realised power", "Deviated power",
                  "Commited flexibility","Realised flexibility", "Deviated flexibility",
                  "Realised commitment costs", "Realised profits",
                  "Average purchase price", "Average feedin price",
                  "Deviation price up","Deviation price down",
                  "Opportunity costs",
                  "Clearing price prognosis negotiations 1",
                  "Clearing price flex negotiations 1",
                  "Clearing price flex negotiations 2",
                  ]

        self.commitment_data = initialize_df(
            columns_commitment_data, environment.start, environment.end, environment.resolution
        )

        self.commitment_data["Opportunity costs"] = 0

        # self.cleared_prognosis_negotiations = DataFrame(
        #     index=initialize_index(
        #         environment.start, environment.end, environment.resolution
        #     ),
        #     columns=["Cleared", "Clearing Price"],
        # )
        #
        # self.cleared_flex_negotiations = DataFrame(
        #     index=initialize_index(
        #         environment.start, environment.end, environment.resolution
        #     ),
        #     columns=["Cleared", "Clearing Price"],
        # )
        #
        # self.realised_power = initialize_series(
        #     None, environment.start, environment.end, environment.resolution
        # )
        # self.sold_flex = initialize_series(
        #     None, environment.start, environment.end, environment.resolution
        # )
        # self.flex_revenues = initialize_series(
        #     None, environment.start, environment.end, environment.resolution
        # )
        # self.opportunity_costs = initialize_series(
        #     0, environment.start, environment.end, environment.resolution
        # )
        # self.prognosis = initialize_series(
        #     None, environment.start, environment.end, environment.resolution
        # )

        self.flex_trade_horizon = flex_trade_horizon
        self.reprognosis_period = reprognosis_period
        self.central_optimization = central_optimization
        # self.flexrequest_parameter["Negotiation rounds"] = flexrequest_rounds


        # Prognosis negotiation inputs
        # self.prognosis_policy = prognosis_policy
        self.prognosis_parameter = prognosis_parameter
        # self.prognosis_q_parameter = prognosis_learning_parameter
        # self.prognosis_q_table_df_1 = DataFrame(
        #     data=0,
        #     index=range(1, prognosis_rounds + 1),
        #     columns=self.prognosis_q_parameter["Action function"](
        #         action=None, markup=None, show_actions=True
        #     ).keys(),
        # )
        # self.prognosis_q_table_df_2 = DataFrame(
        #     data=0,
        #     index=range(1, prognosis_rounds + 1),
        #     columns=self.prognosis_q_parameter["Action function"](
        #         action=None, markup=None, show_actions=True
        #     ).keys(),
        # )
        # self.prognosis_q_table_df_1.index.name = "Rounds"
        # self.prognosis_q_table_df_2.index.name = "Rounds"
        # self.prognosis_action_table_df_1 = deepcopy(self.prognosis_q_table_df_1)
        # self.prognosis_action_table_df_2 = deepcopy(self.prognosis_q_table_df_1)
        #
        # # Flexrequest negotiation inputs
        # self.flexrequest_policy = flexrequest_policy
        self.flexrequest_parameter = flexrequest_parameter
        # self.flexrequest_q_parameter = flexrequest_learning_parameter
        # self.flexrequest_q_table_df_1 = DataFrame(
        #     data=0,
        #     index=range(1, flexrequest_rounds[0] + 1),
        #     columns=self.flexrequest_q_parameter["Action function"](
        #         action=None, markup=None, show_actions=True
        #     ).keys(),
        # )
        # self.flexrequest_q_table_df_2 = DataFrame(
        #     data=0,
        #     index=range(1, flexrequest_rounds[0] + 1),
        #     columns=self.flexrequest_q_parameter["Action function"](
        #         action=None, markup=None, show_actions=True
        #     ).keys(),
        # )
        # self.flexrequest_q_table_df_1.index.name = "Rounds"
        # self.flexrequest_q_table_df_2.index.name = "Rounds"
        # self.flexrequest_action_table_df_1 = deepcopy(self.flexrequest_q_table_df_1)
        # self.flexrequest_action_table_df_2 = deepcopy(self.flexrequest_q_table_df_1)
        #
        # # Storing snapshots for plots
        # self.store_table_steps = linspace(
        #     1, self.environment.total_steps, num=8, dtype="int", endpoint=True
        # )
        # self.stored_q_tables_prognosis_1 = OrderedDict()
        # self.stored_q_tables_prognosis_2 = OrderedDict()
        # self.stored_q_tables_flexrequest_1 = OrderedDict()
        # self.stored_q_tables_flexrequest_2 = OrderedDict()
        # self.stored_action_tables_prognosis_1 = OrderedDict()
        # self.stored_action_tables_prognosis_2 = OrderedDict()
        # self.stored_action_tables_flexrequest_1 = OrderedDict()
        # self.stored_action_tables_flexrequest_2 = OrderedDict()

    def get_commitments(self, time_window: Tuple[datetime, datetime]):
        return [
            select_applicable(
                ems.commitments, (time_window[0], time_window[1]), slice=True
            )
            for ems in self.ems_agents
        ]

    def create_device_message(
        self,
        ems: EMS,
        description: str,
        targeted_power: Series,
        targeted_flexibility: Series,
        order: bool = False,
        deviation_cost_curve: DeviationCostCurve = None,
        costs: float = None,
    ) -> DeviceMessage:

        """Given the Trading Agent's commitments to the Market Agent, and the prognosis for each EMS,
        determine the target schedule for the EMS."""
        i = initialize_index(
            start=self.environment.now,
            end=self.environment.now + self.flex_trade_horizon,
            resolution=self.environment.resolution,
        )
        targeted_power = targeted_power.reindex(i)
        # print("target this power profile")
        # input(targeted_power)

        if order:
            return DeviceMessage(
                type="Order",
                description=description,
                id=self.environment.plan_board.get_message_id(),
                ordered_values=targeted_power,
                targeted_flexibility=targeted_flexibility,
                order=True,
                deviation_cost_curve=deviation_cost_curve,
                costs=costs,
            )
        else:
            return DeviceMessage(
                type="Request",
                description=description,
                id=self.environment.plan_board.get_message_id(),
                requested_values=targeted_power,
                targeted_flexibility=targeted_flexibility,
                order=False,
                deviation_cost_curve=deviation_cost_curve,
            )

    def create_prognosis(self, udi_events: List[UdiEvent]) -> Prognosis:
        """Todoc: write doc string."""
        # Todo: create prognosed values based on udi_events
        prognosed_values = initialize_series(
            data=None,
            start=udi_events[0].start,
            end=udi_events[0].end,
            resolution=udi_events[0].resolution,
        )

        for event in udi_events:
            prognosed_values = prognosed_values.add(
                event.commitment.constants[:], fill_value=0
            )

        return (
            Prognosis(
                id=self.environment.plan_board.get_message_id(),
                start=self.environment.now,
                end=self.environment.now + self.flex_trade_horizon,
                resolution=self.environment.resolution,
                prognosed_values=prognosed_values,
            ),
            udi_events,
        )

    def create_flex_offer(self, flex_request: FlexRequest) -> Tuple[FlexOffer, List[UdiEvent]]:
        """Create a FlexOffer after freely exploring EMS flexibility."""

        # Todo: set aspiration margin
        udi_events_local_memory = []
        udi_event_cnt = 0
        udi_event_costs = float("inf")

        # Either do a central optimisation just for the analysis, or do a flex split
        if self.central_optimization is True:
            # Todo: create a UdiEvent based on central optimization
            best_udi_event = None
            best_udi_events = [None]
        else:
            # Todo: write more flex_split_methods if needed, where each method results in one UdiEvent
            flex_split_methods = [
                equal_flex_split_requested,
                # implement_your_own_flex_split_method_here,
            ]
            aggregated_udi_events = []
            for flex_split_method in flex_split_methods:
                # TODO: Find other way to get absolute flex values and remove environment from arguments then
                output = flex_split_method(
                    self.ems_agents, flex_request, self.environment
                )
                targeted_power = output["target_power"]
                targeted_flexibility = output["target_flex"]

                # Find out how well the EMS agents can fulfil the FlexRequest.
                udi_events = []
                for ems in self.ems_agents:

                    # TODO: Get targeted_flex into device message and store values at EMS
                    for index, row in targeted_flexibility.iteritems():
                        ems.ems_data.loc[index,"Requested flexibility"] = targeted_flexibility.loc[index]

                    # Determine DeviceMessage
                    device_message = self.create_device_message(
                        ems,
                        description="Flex request",
                        targeted_power=targeted_power,
                        targeted_flexibility=targeted_flexibility,
                        deviation_cost_curve=flex_request.commitment.deviation_cost_curve,
                    )

                    # Pull UdiEvent while pushing DeviceMessage to EMS
                    udi_events.append(
                        ems.post_udi_event(ems.get_device_message(device_message))
                    )

                udi_events_local_memory.append(udi_events)

                # Calculate aggregated power values and total costs (private and bid)

                offered_values_aggregated = initialize_series(
                    data=[sum(x) for x in zip(*[udi_event.offered_power.values for udi_event in udi_events])],
                    start=udi_events[0].start,
                    end=udi_events[0].end,
                    resolution=udi_events[0].resolution,
                )

                offered_flexibility_aggregated = initialize_series(
                    data=[sum(x) for x in zip(*[udi_event.offered_flexibility.values for udi_event in udi_events])],
                    start=udi_events[0].start,
                    end=udi_events[0].end,
                    resolution=udi_events[0].resolution,
                )

                offered_costs_aggregated = initialize_series(
                    data=[sum(x) for x in zip(*[udi_event.costs.values for udi_event in udi_events])],
                    start=udi_events[0].start,
                    end=udi_events[0].end,
                    resolution=udi_events[0].resolution,
                )

                # Check if already commited values are same as actual offer values. If true, don't offer them again.
                offered_values_aggregated, offered_flexibility_aggregated, offered_costs_aggregated = \
                    sort_out_already_commited_values(self,
                                                     offered_values_aggregated,
                                                     offered_flexibility_aggregated,
                                                     offered_costs_aggregated)

                #TODO: Check if dev costs and contract costs are still used
                aggregated_udi_events.append(
                    UdiEvent(
                        id=-1,  # Not part of the plan board, as this is just a convenient object for the Trading Agent
                        offered_values=offered_values_aggregated,
                        offered_flexibility=offered_flexibility_aggregated,
                        contract_costs=sum([udi_event.contract_costs for udi_event in udi_events]),
                        deviation_costs=sum([udi_event.deviation_costs for udi_event in udi_events]),
                        deviation_cost_curve=flex_request.commitment.deviation_cost_curve,
                        costs=offered_costs_aggregated,
                    )
                )

            # Todo: choose the best aggregated UdiEvent (implement policies as separate module)
            best_udi_event = None
            for event in aggregated_udi_events:
                if event.costs.sum() < udi_event_costs:
                    best_udi_event = event
                else:
                    pass
                if len(aggregated_udi_events) > 1:
                    udi_event_cnt += 1

        # Unpack opportunity costs for actual horizon
        opportunity_costs = self.commitment_data["Opportunity costs"].loc[
            flex_request.start : flex_request.end - flex_request.resolution
        ]

        # NOTE: Use function call to create one or multiple specific offers after UDI-event aggregation
        # TODO: Move function create_adverse_and_plain_offers from comopt.utils to comopt.model.utils
        # -> There's some (recursive?) issue when loading the dependencies that i couldn't get solved (yet).

        flex_offers = create_adverse_and_plain_offers(self,flex_request, best_udi_event,
                                                      opportunity_costs, self.environment.plan_board)

        # Todo: suggest DeviationCostCurve
        # deviation_cost_curve = DeviationCostCurve(gradient=1, flow_unit_multiplier=self.environment.flow_unit_multiplier)

        #------------- PRINTS ---------------#
        for offer in flex_offers:
            print("\nTA: Costs/Power/Flex {}: {} {} {}\n".format(offer.description, offer.costs, offer.offered_values, offer.offered_flexibility))
            # print("TA: Power {}: {}\n".format(offer.description, )
            # print("TA: Flexibility {}: {}\n".format(offer.description, ))

        # print("\nTA: UDI Event flex: {}\n".format(udi_events_local_memory[udi_event_cnt][0].offered_flexibility))

        return flex_offers, udi_events_local_memory[udi_event_cnt]

    def store_commitment_data(self, commited_power, commited_flexibility):

        start = commited_power.index[0]
        end = commited_power.index[-1]

        for index, row in commited_power.iteritems():

            if not isnull(commited_power.loc[index]):

                self.commitment_data.loc[index,"Commited power"] = commited_power.loc[index]
                self.commitment_data.loc[index,"Commited flexibility"] = commited_flexibility.loc[index]

        print("TA: Commited power: {}\n".format(self.commitment_data.loc[start:end,"Commited power"]))
        print("TA: Commited flexbility: {}\n".format(self.commitment_data.loc[start:end,"Commited flexibility"]))

        return

    def step(self):

        print("+++++++++++++++++++++ NEW STEP +++++++++++++++++++++    TIME: {}\n".format(self.environment.now))

        # Pull market agent request for prognosis
        prognosis_request = self.market_agent.post_prognosis_request()
        # Add prognosis request to plan board
        self.environment.plan_board.store_message(
            timeperiod=self.environment.now,
            message=prognosis_request,
            keys=["TA", "MA"],
        )

        # Decision Gate 1: TA and MA bargain over prognosis price

        # Update parameters related to q-learning
        # self.prognosis_q_parameter["Step now"] = self.environment.step_now
        print("---------------------PROGNOSIS NEGOTIATION--------------------------")

        update_adaptive_strategy_data(description="Prognosis",
                                      ta_parameter=self.prognosis_parameter,
                                      plan_board=self.environment.plan_board,
                                      timeperiod_now=self.environment.now,
                                      step_now=self.environment.step_now,
                                      snapshot=True)

        prognosis_decision = start_negotiation(
            description="Prognosis",
            environment_now=self.environment.now,
            ta_parameter=self.prognosis_parameter,
            ma_parameter=self.environment.market_agent.prognosis_parameter,
            plan_board=self.environment.plan_board,
            negotiation_log=self.environment.plan_board.prognosis_negotiations_log,
        )

        # If the negotiation got cleared let the model continue, otherwise proceed to next step of simulation horizon
        if "Not Cleared" in prognosis_decision["Status"]:
            self.commitment_data.loc[self.environment.now, "Clearing price prognosis negotiations 1"] = nan
            return
        else:
            print("TA: Prognosis negotiation status: AGREEMENT\n")
            self.commitment_data.loc[self.environment.now, "Clearing price prognosis negotiations 1"] = prognosis_decision["Clearing price"]
            pass

        # Pull UdiEvents while pushing empty DeviceMessages to each EMS
        print("---------------------PROGNOSIS UDI EVENTS--------------------------")
        udi_events = []
        for ems in self.ems_agents:
            # Create empty device message
            device_message = self.create_device_message(
                ems,
                description="Prognosis data",
                targeted_power=initialize_series(
                    None,
                    self.environment.now,
                    self.environment.now + self.flex_trade_horizon,
                    self.environment.resolution,
                ),
                targeted_flexibility=initialize_series(
                    0,
                    self.environment.now,
                    self.environment.now + self.flex_trade_horizon,
                    self.environment.resolution,
                ),
                deviation_cost_curve=DeviationCostCurve(
                    gradient=0,
                    flow_unit_multiplier=self.environment.flow_unit_multiplier,
                ),
            )
            # Add DeviceMessage to plan board
            self.environment.plan_board.store_message(timeperiod=self.environment.now, message=device_message, keys=[ems.name])

            # Get UDI event
            udi_events.append(ems.post_udi_event(device_message))

        # Add UDI events to plan board
        for event in udi_events:
            self.environment.plan_board.store_message(timeperiod=self.environment.now, message=event, keys=[ems.name])

        # Determine Prognosis
        prognosis, prognosis_udi_events = self.create_prognosis(udi_events)

        print("TA: Prognosis event flexibility: {}".format(prognosis_udi_events[0].offered_flexibility))

        # Add Prognosis to planboard message log
        self.environment.plan_board.store_message(timeperiod=self.environment.now, message=prognosis, keys=["TA", "MA"])

        # TODO: Decision Gate 2: If prognosis is very interesting, than another negotiation over the prognosis price starts

        # Pull FlexRequest while pushing Prognosis to MA
        flex_request = self.market_agent.post_flex_request(self.market_agent.get_prognosis(prognosis))

        # Add message to plan board
        self.environment.plan_board.store_message(timeperiod=self.environment.now, message=flex_request, keys=["TA", "MA"])

        # Determine FlexOffer (could be multiple offers)
        flex_offers, flex_offer_udi_events = self.create_flex_offer(flex_request)

        print("TA: Flexrequest udi event flexibility: {}\n".format(flex_offer_udi_events[0].offered_flexibility))

        # Flex Decision Gate 1: TA and MA bargain over flex request price
        update_adaptive_strategy_data(description="Flexrequest",
                                      ta_parameter=self.flexrequest_parameter,
                                      plan_board=self.environment.plan_board,
                                      timeperiod_now=self.environment.now,
                                      step_now=self.environment.step_now,
                                      snapshot=True)

        for enum, offer in enumerate(flex_offers):

            self.flexrequest_parameter["Reservation price"] = offer.costs.sum(axis="index")

            # Submit flexoffer with adverse costs to MA
            self.market_agent.get_flex_offer(offer)
            self.environment.plan_board.store_message(
                timeperiod=self.environment.now, message=offer, keys=["TA", "MA"])

            print("TA: Market agent reservation price {}\n".format(self.environment.market_agent.flexrequest_parameter["Reservation price"]))
            print("TA: Trading agent reservation price {}\n".format(self.flexrequest_parameter["Reservation price"]))

            flexrequest_decision = start_negotiation(
                description=offer.description,
                environment_now=self.environment.now,
                ta_parameter=self.flexrequest_parameter,
                ma_parameter=self.environment.market_agent.flexrequest_parameter,
                plan_board=self.environment.plan_board,
                negotiation_log=self.environment.plan_board.flexrequest_negotiations_log,
            )

            print("TA: Flex negotiation status: {}\n".format(flexrequest_decision["Status"]))
            print("TA: Flex negotiation clearing price: {}\n".format(flexrequest_decision["Clearing price"]))
            print("----------------------DATA VALUE UPDATE--------------------------       TIME: {} \n".format(self.environment.now))

            if "NOT CLEARED" in flexrequest_decision["Status"]:

                # Check if another offer is available and continue with the next negotiation
                if enum is not len(flex_offers)-1:
                    print("Next Round")
                    print("TA: Next offer: {}".format(offer[enum+1]))
                    continue

                # If there is no offer left to bargain over, save agents data and return
                else:

                    for ems, event in zip(self.ems_agents, prognosis_udi_events):

                        print("TA: Store prognosis flex as commited: {}".format(event.offered_flexibility.loc[offer.start:offer.end - offer.resolution]))

                        # Assign the prognosed udi event values to a device message, and pass it to the EMS for storing data and commitment
                        ems.store_data(
                            commitments=event.commitment,
                            device_message= self.create_device_message(ems,
                                                                       description="Failed Negotiation",
                                                                       targeted_power=event.offered_values.loc[offer.start:offer.end - offer.resolution],
                                                                       targeted_flexibility=event.offered_flexibility.loc[offer.start:offer.end - offer.resolution],
                                                                       deviation_cost_curve=(0,0),
                                                                       costs=event.costs,
                                                                       order=True),
                                        )
                    return

            # "CLEARED"
            else:
                # Assign the offered udi event values to a device message, and pass it to the EMS for storing data and commitment
                for ems, event in zip(self.ems_agents, flex_offer_udi_events):

                    print("TA: Cleared negotiaton over {}\n".format(offer.description))

                    commited_power = deepcopy(event.offered_values)
                    commited_flexibility = deepcopy(event.offered_flexibility)

                    # This loop cuts already commited values from actual offer (-> applicable commitments)
                    for index, row in offer.offered_values.iteritems():

                        if isnull(offer.offered_flexibility.loc[index]):
                            commited_flexibility.loc[index] = nan

                        if isnull(offer.offered_values.loc[index]):
                            commited_power.loc[index] = nan

                    self.store_commitment_data(commited_power,commited_flexibility)

                    ems.store_data(
                        commitments=event.commitment,
                        device_message= self.create_device_message(
                                                                    ems,
                                                                    description="Succeeded Negotiation",
                                                                    targeted_power=commited_power,
                                                                    targeted_flexibility=commited_flexibility,
                                                                    deviation_cost_curve=flex_request.commitment.deviation_cost_curve,
                                                                    costs=event.costs,
                                                                    order=True
                                                                    ),
                    )

                # Pull FlexOrder by pushing FlexOffer to MA
                flex_order = self.market_agent.post_flex_order(
                    self.market_agent.get_flex_offer(flex_offer=offer, order=True)
                )

                #Add Order to planboard message log
                self.environment.plan_board.store_message(timeperiod=self.environment.now, message=flex_order, keys=["TA", "MA"])

            return

            # Update opportunity costs
            # Todo: the following line assumes that the new commitments have already been stored in the EMS.commitments attribute (so the TA should do that in store_flex_order()!)
            # previous_commitments_and_new_commitment = self.get_commitments(
            #     (flex_order.start, flex_order.end)
            # )
            # self.opportunity_costs.loc[
            #     flex_order.start : flex_order.end - flex_order.resolution
            # ] = determine_opportunity_costs_model_a(
            #     previous_commitments_and_new_commitment,
            #     flex_order.start,
            #     flex_order.end,
            #     flex_order.resolution,
            # )
            # Todo: repeat until one of the stop conditions is met (you have an agreement, or max number of rounds (part of the protocol) is reached)


                    # ems.store_commitment_data(udi_event=event)
                # ems.realised_power_per_device.loc[self.environment.now, :] = (
                #     ems.planned_power_per_device.loc[self.environment.now, :]
                #     - ems.planned_flex_per_device.loc[self.environment.now, :]
                # )
                # ems.realised_costs_over_horizons[
                #     self.environment.now
                # ] = ems.prognosed_costs_over_horizons[self.environment.now]
                # # ems.realised_flex_per_device.loc[self.environment.now,:] = ems.prognosed_flex_per_device.loc[self.environment.now,:]
                # print(
                #     "TA: Realised flex per device: {}\n \n".format(
                #         ems.realised_flex_per_device
                #     )
                # )
                # print(
                #     "TA: Realised power per device: {}\n \n".format(
                #         ems.realised_power_per_device
                #     )
                # )
                # self.store_commitment_data(prognosis, prognosis_udi_events)

        # else:
        #     flex_offer.costs = flexrequest_decision_gate_1["Clearing price"]
        #     # TODO: Use negotiationlog file instead of instance variables
        #     self.cleared_flex_negotiations.loc[self.environment.now, "Cleared"] = 1
        #     self.cleared_flex_negotiations.loc[
        #         self.environment.now, "Clearing Price"
        #     ] = flexrequest_decision_gate_1["Clearing price"]
        #
        #     for ems in self.ems_agents:
        #
        #         ems.realised_power_per_device.loc[
        #             self.environment.now, :
        #         ] = ems.planned_power_per_device.loc[self.environment.now, :]
        #
        #         ems.realised_flex_per_device.loc[
        #             self.environment.now, :
        #         ] = ems.planned_flex_per_device.loc[self.environment.now, :]
        #
        #         ems.realised_costs_over_horizons[
        #             self.environment.now
        #         ] = ems.planned_costs_over_horizons[self.environment.now]
        #
        #     idx = flex_offer.commitment.constants.index
        #     for row, val in enumerate(
        #         flex_offer.commitment.constants.loc[
        #             flex_offer.start : (flex_offer.end - flex_offer.resolution),
        #         ]
        #     ):
        #         if val != flex_offer.prognosis.commitment.constants[row]:
        #             self.market_agent.commitments.loc[
        #                 idx[row], "agreed_flex"
        #             ] = self.market_agent.commitments.loc[idx[row], "negotiated_flex"]
        #     # self.market_agent.commitments.loc[self.environment.now:, "received_flex"] = self.market_agent.commitments.loc[self.environment.now:, "agreed_flex"]
        #     print(
        #         "TA: MA AGREED flex: {} \n \n".format(
        #             self.market_agent.commitments["agreed_flex"]
        #         )
        #     )
        #     print(
        #         "TA: MA RECEIVED FLEX: {} \n \n".format(
        #             self.market_agent.commitments.loc[
        #                 self.environment.now, "received_flex"
        #             ]
        #         )
        #     )
        #     print("TA: EMS REALISED FLEX: {}\n \n".format(ems.realised_flex_per_device))
        #
        #
        #
        #     # Update commitments (due to FlexOrder)
        #     if flex_order is not None:
        #         # TODO: Store values at EMS
        #         self.store_commitment(flex_order, flex_offer_udi_events)
