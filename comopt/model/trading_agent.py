from typing import Callable, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from numpy import linspace
from pandas import DataFrame, Series, concat
from copy import deepcopy
from collections import OrderedDict

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
    start_negotiation,
    table_snapshots,
)
from comopt.utils import Agent
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
        prognosis_horizon: timedelta,
        reprognosis_period: timedelta,
        prognosis_policy: Callable,
        prognosis_parameter: dict,
        prognosis_rounds: int,
        prognosis_learning_parameter: dict,
        flexrequest_policy: Callable,
        flexrequest_parameter: dict,
        flexrequest_rounds: int,
        flexrequest_learning_parameter: dict,
        central_optimization: bool = False,
    ):
        """ Creates an instance of the Class TradingAgent. Inherits from the Class Agent."""
        super().__init__(name, environment)

        self.market_agent = market_agent
        self.ems_agents = ems_agents

        self.cleared_prognosis_negotiations = DataFrame(
            index=initialize_index(
                environment.start, environment.end, environment.resolution
            ),
            columns=["Cleared", "Clearing Price"],
        )

        self.cleared_flex_negotiations = DataFrame(
            index=initialize_index(
                environment.start, environment.end, environment.resolution
            ),
            columns=["Cleared", "Clearing Price"],
        )

        self.realised_power = initialize_series(
            None, environment.start, environment.end, environment.resolution
        )
        self.sold_flex = initialize_series(
            None, environment.start, environment.end, environment.resolution
        )
        self.flex_revenues = initialize_series(
            None, environment.start, environment.end, environment.resolution
        )
        self.opportunity_costs = initialize_series(
            0, environment.start, environment.end, environment.resolution
        )
        self.prognosis = initialize_series(
            None, environment.start, environment.end, environment.resolution
        )
        self.expected_prognosis_range = initialize_series(
            None, environment.start, environment.end, environment.resolution
        )
        self.prognosis_horizon = prognosis_horizon
        self.reprognosis_period = reprognosis_period
        self.central_optimization = central_optimization

        # Prognosis negotiation inputs
        self.prognosis_policy = prognosis_policy
        self.prognosis_parameter = prognosis_parameter
        self.prognosis_q_parameter = prognosis_learning_parameter
        self.prognosis_q_table_df_1 = DataFrame(
            data=0,
            index=range(1, prognosis_rounds + 1),
            columns=self.prognosis_q_parameter["Action function"](
                action=None, markup=None, show_actions=True
            ).keys(),
        )
        self.prognosis_q_table_df_2 = DataFrame(
            data=0,
            index=range(1, prognosis_rounds + 1),
            columns=self.prognosis_q_parameter["Action function"](
                action=None, markup=None, show_actions=True
            ).keys(),
        )
        self.prognosis_q_table_df_1.index.name = "Rounds"
        self.prognosis_q_table_df_2.index.name = "Rounds"
        self.prognosis_action_table_df_1 = deepcopy(self.prognosis_q_table_df_1)
        self.prognosis_action_table_df_2 = deepcopy(self.prognosis_q_table_df_1)

        # Flexrequest negotiation inputs
        self.flexrequest_policy = flexrequest_policy
        self.flexrequest_parameter = flexrequest_parameter
        self.flexrequest_q_parameter = flexrequest_learning_parameter
        self.flexrequest_q_table_df_1 = DataFrame(
            data=0,
            index=range(1, flexrequest_rounds + 1),
            columns=self.flexrequest_q_parameter["Action function"](
                action=None, markup=None, show_actions=True
            ).keys(),
        )
        self.flexrequest_q_table_df_2 = DataFrame(
            data=0,
            index=range(1, flexrequest_rounds + 1),
            columns=self.flexrequest_q_parameter["Action function"](
                action=None, markup=None, show_actions=True
            ).keys(),
        )
        self.flexrequest_q_table_df_1.index.name = "Rounds"
        self.flexrequest_q_table_df_2.index.name = "Rounds"
        self.flexrequest_action_table_df_1 = deepcopy(self.flexrequest_q_table_df_1)
        self.flexrequest_action_table_df_2 = deepcopy(self.flexrequest_q_table_df_1)

        # Storing snapshots for plots
        self.store_table_steps = linspace(
            1, self.environment.total_steps, num=8, dtype="int", endpoint=True
        )
        self.stored_q_tables_prognosis_1 = OrderedDict()
        self.stored_q_tables_prognosis_2 = OrderedDict()
        self.stored_q_tables_flexrequest_1 = OrderedDict()
        self.stored_q_tables_flexrequest_2 = OrderedDict()
        self.stored_action_tables_prognosis_1 = OrderedDict()
        self.stored_action_tables_prognosis_2 = OrderedDict()
        self.stored_action_tables_flexrequest_1 = OrderedDict()
        self.stored_action_tables_flexrequest_2 = OrderedDict()

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
            end=self.environment.now + self.prognosis_horizon,
            resolution=self.environment.resolution,
        )
        targeted_power = targeted_power.reindex(i)
        # print("target this power profile")
        # input(targeted_power)

        if order:
            return DeviceMessage(
                id=self.environment.plan_board.get_message_id(),
                ordered_values=targeted_power,
                targeted_flexibility=targeted_flexibility,
                order=True,
                deviation_cost_curve=deviation_cost_curve,
                costs=costs,
            )
        else:
            return DeviceMessage(
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
                end=self.environment.now + self.prognosis_horizon,
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

        aspiration_margin = 0
        opportunity_costs = self.opportunity_costs.loc[
            flex_request.start : flex_request.end - flex_request.resolution
        ]

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
                    for idx in targeted_flexibility.index:
                        ems.ems_data.loc[idx,"Requested flexibility"] = targeted_flexibility.loc[idx]

                    # Determine DeviceMessage
                    device_message = self.create_device_message(
                        ems,
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

                # Aggregate offered flexibility
                offered_flexibility_aggregated = Series(data=0,index=udi_events[0].offered_flexibility.index)

                for event in udi_events:
                    offered_flexibility_aggregated += event.offered_flexibility

                offered_flexibility_aggregated = initialize_series(
                    data=offered_flexibility_aggregated,
                    start=udi_events[0].start,
                    end=udi_events[0].end,
                    resolution=udi_events[0].resolution,
                )

                aggregated_udi_events.append(
                    UdiEvent(
                        id=-1,  # Not part of the plan board, as this is just a convenient object for the Trading Agent
                        offered_values=offered_values_aggregated,
                        offered_flexibility=offered_flexibility_aggregated,
                        contract_costs=sum([udi_event.contract_costs for udi_event in udi_events]),
                        deviation_costs=sum([udi_event.deviation_costs for udi_event in udi_events]),
                        costs=sum([udi_event.costs for udi_event in udi_events]),
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

        # Store contract_costs and deviation_costs of the best UDI-Event
        contract_costs_best_udi_event = best_udi_event.contract_costs
        deviation_costs_best_udi_event = best_udi_event.deviation_costs

        # Create Adverse_flexoffer: Offered power and offered flexibility values comply with the requested ones.
        #                           Commitment costs include deviation costs for each datetime where the EM-Systems plan to deviate.

        adverse_values = flex_request.requested_values.loc[
                         flex_request.start : (flex_request.end - flex_request.resolution)]

        adverse_flexibility = flex_request.requested_flexibility.loc[
                              flex_request.start : (flex_request.end - flex_request.resolution)]

        # Markup is relative to the costs and gets used as a multiplier
        commitment_costs_best_udi_event = best_udi_event.costs

        adverse_flex_offer = FlexOffer(
                                      id=self.environment.plan_board.get_message_id(),
                                      offered_values=adverse_values,
                                      offered_flexibility=adverse_flexibility,
                                      deviation_cost_curve=flex_request.commitment.deviation_cost_curve,
                                      costs=commitment_costs_best_udi_event,
                                      flex_request=flex_request,
                                      )

        # Create Plain_flexoffer: Offered values and offered flexibility comply with the planned values of the EM-Systems.
        #                         Commitment costs include only the cost difference of the contract costs.

        plain_values = best_udi_event.offered_power.loc[
                       flex_request.start : (flex_request.end - flex_request.resolution)]

        plain_flexibility = best_udi_event.offered_flexibility.loc[
                            flex_request.start : (flex_request.end - flex_request.resolution)]

        commitment_costs_best_udi_event = (best_udi_event.costs - deviation_costs_best_udi_event)

        plain_flex_offer = FlexOffer(
                                    id=self.environment.plan_board.get_message_id(),
                                    offered_values=plain_values,
                                    offered_flexibility=plain_flexibility,
                                    deviation_cost_curve=flex_request.commitment.deviation_cost_curve,
                                    costs=commitment_costs_best_udi_event,
                                    flex_request=flex_request,
                                   )

        # Todo: suggest DeviationCostCurve
        # deviation_cost_curve = DeviationCostCurve(gradient=1, flow_unit_multiplier=self.environment.flow_unit_multiplier)

        #------------- PRINTS ---------------#
        print("\nTA: Costs adverse_flexoffer: {}\n".format(adverse_flex_offer.costs))
        print("TA: Costs plain_flexoffer: {}\n".format(plain_flex_offer.costs))
        print("TA: Power adverse_flexoffer: {}\n".format(adverse_flex_offer.offered_values))
        print("TA: Power plain_flexoffer: {}\n".format(plain_flex_offer.offered_values))
        print("TA: Flexibility adverse_flexoffer: {}\n".format(adverse_flex_offer.offered_flexibility))
        print("TA: Flexibility plain_flexoffer: {}\n".format(plain_flex_offer.offered_flexibility))

        return (adverse_flex_offer,
                plain_flex_offer,
                udi_events_local_memory[udi_event_cnt],
                )

    def store_commitment(self, com: Union[Prognosis, FlexOrder], udi_events: List[UdiEvent]):

        if com.commitment.deviation_cost_curve is None:
            gradient_down = 0
            gradient_up = 0
        else:
            gradient_down = com.commitment.deviation_cost_curve.gradient_down
            gradient_up = com.commitment.deviation_cost_curve.gradient_up

        for ems, udi_event in zip(self.ems_agents, udi_events):
            ems_commitment = Commitment(
                label=None,
                constants=udi_event.commitment.constants,
                costs=udi_event.costs,
                deviation_cost_curve=DeviationCostCurve(
                    gradient=(gradient_down, gradient_up),
                    # keep 1 as value here
                    flow_unit_multiplier=1,
                ),
            )
            ems.commitments.append(ems_commitment)

    def step(self):

        print("%%%%%%%%%%%%%% NEW STEP %%%%%%%%%%%%%%    TIME: {}\n".format(self.environment.now))

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
        self.prognosis_q_parameter["Step now"] = self.environment.step_now
        print("---------------------PROGNOSIS NEGOTIATION--------------------------")

        table_snapshots(
            snapshots=self.store_table_steps,
            step_now=self.environment.step_now,
            timeperiod_now=self.environment.now,
            stored_q_tables=self.stored_q_tables_prognosis_1,
            stored_action_tables=self.stored_action_tables_prognosis_1,
            q_table_now=self.prognosis_q_table_df_1,
            action_table_now=self.prognosis_action_table_df_1,
        )

        prognosis_decision_gate_1 = start_negotiation(
            type="Prognosis",
            datetime=self.environment.now,
            rounds_total=self.environment.plan_board.prognosis_negotiation_log_1.index.get_level_values("Round").max(),
            ta_policy=self.prognosis_policy,
            ta_parameter=self.prognosis_parameter,
            ma_policy=self.environment.market_agent.prognosis_policy,
            ma_parameter=self.environment.market_agent.prognosis_parameter,
            negotiation_data_df=self.environment.plan_board.prognosis_negotiation_log_1,
            action_table_df=self.prognosis_action_table_df_1,
            q_table_df=self.prognosis_q_table_df_1,
            q_parameter=self.prognosis_q_parameter,
        )

        # If the negotiation got cleared let the model continue, otherwise proceed to next step of simulation horizon
        if "Not Cleared" in prognosis_decision_gate_1["Status"]:
            print("TA: Prognosis negotiation status: NO AGREEMENT \n")
            return
        else:
            print("TA: Prognosis negotiation status: AGREEMENT\n")
            self.cleared_prognosis_negotiations.loc[self.environment.now, "Cleared"] = 1
            self.cleared_prognosis_negotiations.loc[
                self.environment.now, "Clearing Price"
            ] = prognosis_decision_gate_1["Clearing price"]
            pass

        # Pull UdiEvents while pushing empty DeviceMessages to each EMS
        print("---------------------PROGNOSIS UDI EVENTS--------------------------")
        udi_events = []
        for ems in self.ems_agents:
            # Create empty device message
            device_message = self.create_device_message(
                ems,
                targeted_power=initialize_series(
                    None,
                    self.environment.now,
                    self.environment.now + self.prognosis_horizon,
                    self.environment.resolution,
                ),
                targeted_flexibility=initialize_series(
                    0,
                    self.environment.now,
                    self.environment.now + self.prognosis_horizon,
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

        # Add Prognosis to planboard message log
        self.environment.plan_board.store_message(timeperiod=self.environment.now, message=prognosis, keys=["TA", "MA"])

        # TODO: Decision Gate 2: If prognosis is very interesting, than another negotiation over the prognosis price starts

        # Pull FlexRequest while pushing Prognosis to MA
        flex_request = self.market_agent.post_flex_request(self.market_agent.get_prognosis(prognosis))

        # Add message to plan board
        self.environment.plan_board.store_message(timeperiod=self.environment.now, message=flex_request, keys=["TA", "MA"])

        # print(flex_request.requested_flex)
        print("TA: Requested power values in kWh: {}\n".format(flex_request.requested_values))
        print("TA: Requested flex values in kWh: {}\n".format(flex_request.requested_flexibility))

        print("---------------------FLEX UDI EVENTS--------------------------      TIME: {}".format(self.environment.now))

        # Determine FlexOffer (could be multiple offers)
        adverse_flex_offer, plain_flex_offer, flex_offer_udi_events = self.create_flex_offer(flex_request)

        # MA stores negotiated flex
        self.market_agent.get_flex_offer(adverse_flex_offer)
        self.environment.plan_board.store_message(
            timeperiod=self.environment.now, message=adverse_flex_offer, keys=["TA", "MA"]
        )

        # Reservation values: TA = flex offer costs; MA = flex offer costs * Reservation factor
        self.flexrequest_parameter["Reservation price"] = adverse_flex_offer.costs.sum()

        # flex_offer_plus_deviation_costs = flex_offer.costs
        # cost_only_flex = flex_offer.offered_flex.values.sum() * 1

        # print("TA: Flex offer cost including deviation: {}\n".format(d))
        # print("TA: Flex offer cost only flex: {}\n \n".format(cost_only_flex))
        # print("TA: Flex offer planned flex: {}\n \n".format(flex_offer.planned_flex))
        # print(
        #     "TA: Planned - Requested flex: {}\n".format(
        #         flex_offer.planned_flex - flex_request.requested_flex
        #     )
        # )

        # print("TA: Market agent reservation price {}".format(self.environment.market_agent.imbalance_market_costs.loc[self.environment.now]))

        # print(prognosis.commitment.costs)
        self.environment.market_agent.flexrequest_parameter["Reservation price"] = sum(
            self.environment.market_agent.imbalance_market_costs.loc[
                self.environment.now : self.environment.now + self.prognosis_horizon
            ]
        )
        # self.flexrequest_parameter["Reservation price"] = (flex_offer.costs)  # + self.environment.ems_agents[0].planned_flex_per_device.sum().sum() * 6
        print("TA: Flex offer costs: {}\n".format(self.flexrequest_parameter["Reservation price"]))
        print("TA: Market agent reservation price {}\n".format(self.environment.market_agent.flexrequest_parameter["Reservation price"]))
        # Markup values: TA = flex offer costs*; MA = flex offer costs * Reservation factor
        # self.flexrequest_parameter["Markup"] = abs(flex_offer.costs) * self.flexrequest_parameter["Markup factor"]
        # self.environment.market_agent.flexrequest_parameter["Markup"] = abs(flex_offer.costs) * self.environment.market_agent.flexrequest_parameter["Markup factor"]

        # Flex Decision Gate 1: TA Res = cost()

        # Flex Decision Gate 1: TA and MA bargain over flex request price
        table_snapshots(
            snapshots=self.store_table_steps,
            step_now=self.environment.step_now,
            timeperiod_now=self.environment.now,
            stored_q_tables=self.stored_q_tables_flexrequest_1,
            stored_action_tables=self.stored_action_tables_flexrequest_1,
            q_table_now=self.flexrequest_q_table_df_1,
            action_table_now=self.flexrequest_action_table_df_1,
        )

        flexrequest_decision_gate_1 = start_negotiation(
            type="Flexrequest",
            datetime=self.environment.now,
            rounds_total=self.environment.plan_board.flexrequest_negotiation_log_1.index.get_level_values("Round").max(),
            ta_policy=self.flexrequest_policy,
            ta_parameter=self.flexrequest_parameter,
            ma_policy=self.environment.market_agent.flexrequest_policy,
            ma_parameter=self.environment.market_agent.flexrequest_parameter,
            negotiation_data_df=self.environment.plan_board.flexrequest_negotiation_log_1,
            action_table_df=self.flexrequest_action_table_df_1,
            q_table_df=self.flexrequest_q_table_df_1,
            q_parameter=self.flexrequest_q_parameter,
        )

        print("\nTA: Flex negotiation status: {}\n".format(flexrequest_decision_gate_1["Status"]))
        print("TA: Flex negotiation clearing price: {}\n".format(flexrequest_decision_gate_1["Clearing price"]))

        print("----------------------REALISED VALUES UPDATE--------------------------       TIME: {} \n".format(self.environment.now))

        horizon = self.environment.now + self.prognosis_horizon
        if "NOT CLEARED" in flexrequest_decision_gate_1["Status"]:
            # TODO: Store values at EMS
            for ems in self.ems_agents:
                # TODO prove if that holds for devices with negative flex capability
                ems.realised_power_per_device.loc[self.environment.now, :] = (
                    ems.planned_power_per_device.loc[self.environment.now, :]
                    - ems.planned_flex_per_device.loc[self.environment.now, :]
                )
                ems.realised_costs_over_horizons[
                    self.environment.now
                ] = ems.prognosed_costs_over_horizons[self.environment.now]
                # ems.realised_flex_per_device.loc[self.environment.now,:] = ems.prognosed_flex_per_device.loc[self.environment.now,:]
                print(
                    "TA: Realised flex per device: {}\n \n".format(
                        ems.realised_flex_per_device
                    )
                )
                print(
                    "TA: Realised power per device: {}\n \n".format(
                        ems.realised_power_per_device
                    )
                )
                self.store_commitment(prognosis, prognosis_udi_events)
            return

        else:
            flex_offer.costs = flexrequest_decision_gate_1["Clearing price"]
            # TODO: Use negotiationlog file instead of instance variables
            self.cleared_flex_negotiations.loc[self.environment.now, "Cleared"] = 1
            self.cleared_flex_negotiations.loc[
                self.environment.now, "Clearing Price"
            ] = flexrequest_decision_gate_1["Clearing price"]
            for ems in self.ems_agents:
                ems.realised_power_per_device.loc[
                    self.environment.now, :
                ] = ems.planned_power_per_device.loc[self.environment.now, :]
                ems.realised_flex_per_device.loc[
                    self.environment.now, :
                ] = ems.planned_flex_per_device.loc[self.environment.now, :]
                ems.realised_costs_over_horizons[
                    self.environment.now
                ] = ems.planned_costs_over_horizons[self.environment.now]

            idx = flex_offer.commitment.constants.index
            for row, val in enumerate(
                flex_offer.commitment.constants.loc[
                    flex_offer.start : (flex_offer.end - flex_offer.resolution),
                ]
            ):
                if val != flex_offer.prognosis.commitment.constants[row]:
                    self.market_agent.commitments.loc[
                        idx[row], "agreed_flex"
                    ] = self.market_agent.commitments.loc[idx[row], "negotiated_flex"]
            # self.market_agent.commitments.loc[self.environment.now:, "received_flex"] = self.market_agent.commitments.loc[self.environment.now:, "agreed_flex"]
            print(
                "TA: MA AGREED flex: {} \n \n".format(
                    self.market_agent.commitments["agreed_flex"]
                )
            )
            print(
                "TA: MA RECEIVED FLEX: {} \n \n".format(
                    self.market_agent.commitments.loc[
                        self.environment.now, "received_flex"
                    ]
                )
            )
            print("TA: EMS REALISED FLEX: {}\n \n".format(ems.realised_flex_per_device))

            # Pull FlexOrder by pushing FlexOffer to MA
            flex_order = self.market_agent.post_flex_order(
                self.market_agent.get_flex_offer(flex_offer)
            )

            # Update commitments (due to FlexOrder)
            if flex_order is not None:
                # TODO: Store values at EMS
                self.store_commitment(flex_order, flex_offer_udi_events)

            # Add Order to planboard message log
            # self.environment.plan_board.store_message(timeperiod=self.environment.now, message=order, keys=["TA", "MA"])

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
