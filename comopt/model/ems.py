from typing import List, Optional, Tuple

from pandas import DataFrame, Series, isnull
from numpy import array, nan, isnan

from comopt.data_structures.commitments import (
    DeviationCostCurve,
    PiecewiseConstantProfileCommitment as Commitment,
)
from comopt.data_structures.usef_message_types import DeviceMessage, UdiEvent
from comopt.data_structures.utils import select_applicable
from comopt.model.utils import initialize_df, initialize_series
from comopt.solver.ems_solver import device_scheduler
from comopt.utils import Agent


class EMS(Agent):
    """
    A Prosumer-type agent that has several (shiftable) consumer devices like photovoltaic panels, batteries, EV, under
    its control.
    """

    def __init__(
        self,
        name,
        environment,
        devices: List[Tuple[str, DataFrame]],
        ems_constraints: DataFrame,
        ems_prices: Tuple[float],
    ):
        super().__init__(name, environment)
        self.devices = range(
            len(devices)
        )  # We don't really need Device objects, so for now we just number them
        self.device_types = [device[0] for device in devices]
        self.device_constraints = [device[1] for device in devices]
        # computes the ems net demand from device constraints -> works only without battery and buffer (otherwise perform optimization over simulation runtime here)
        self.ems_constraints = ems_constraints
        self.device_messages_cnt = 1
        self.commitments = [
            Commitment(
                label="Energy contract",
                constants=initialize_series(
                    0,
                    self.environment.start,
                    self.environment.end,
                    self.environment.resolution,
                ),
                deviation_cost_curve=DeviationCostCurve(
                    function_type="Linear",
                    gradient=ems_prices,
                    flow_unit_multiplier=self.environment.flow_unit_multiplier,
                ),
            )
        ]  # The initial commitment simply states prices for consuming and producing (i.e. for deviating from 0)

        #TODO: Loop and refactor
        #TODO: use planboard messages insteat of instance variable
        self.device_messages = initialize_series(start=self.environment.start,end=self.environment.end,
                                                resolution=self.environment.resolution, data=0)

        self.targeted_flex = initialize_series(start=self.environment.start,end=self.environment.end,
                                                resolution=self.environment.resolution, data=0)

        self.prognosed_over_horizons = DataFrame(index=self.commitments[0].constants.index,
                                        columns=["Load", "Generation", "Battery", "Buffer"])

        self.prognosed_power_per_device = DataFrame(index=self.commitments[0].constants.index,
                                        columns=["Load", "Generation", "Battery", "Buffer"])

        self.planned_over_horizons = DataFrame(index=self.commitments[0].constants.index,
                                        columns=["Load", "Generation", "Battery", "Buffer"])

        self.planned_power_per_device = DataFrame(index=self.commitments[0].constants.index,
                                        columns=["Load", "Generation", "Battery", "Buffer"])

        self.realised_over_horizons = DataFrame(index=self.commitments[0].constants.index,
                                        columns=["Load", "Generation", "Battery", "Buffer"])

        self.realised_power_per_device = DataFrame(index=self.commitments[0].constants.index,
                                        columns=["Load", "Generation", "Battery", "Buffer"])

        self.flex_over_horizons = DataFrame(index=self.commitments[0].constants.index,
                                        columns=["Load", "Generation", "Battery", "Buffer"])
        # not used yet
        self.prognosed_flex_per_device = DataFrame(index=self.commitments[0].constants.index,
                                        columns=["Load", "Generation", "Battery", "Buffer"])

        self.planned_flex_per_device = DataFrame(index=self.commitments[0].constants.index,
                                        columns=["Load", "Generation", "Battery", "Buffer"])

        self.realised_flex_per_device = DataFrame(index=self.commitments[0].constants.index,
                                        columns=["Load", "Generation", "Battery", "Buffer"])

        self.prognosed_costs_over_horizons = dict()
        self.planned_costs_over_horizons = dict()
        self.realised_costs_over_horizons = dict()


    def post_udi_event(self, device_message: DeviceMessage) -> UdiEvent:
        """Callback function to have the EMS create and post a UdiEvent."""

        # TODO: use planboard messages insteat of instance variable
        self.device_messages.loc[device_message.start] = device_message

        # Todo: create udi_event based on targets (from FlexRequest), by including the target in the previous commitments lists
        device_constraints = [
            device_constraints.loc[
                device_message.start : device_message.end - device_message.resolution
            ]
            for device_constraints in self.device_constraints
        ]
        ems_constraints = self.ems_constraints.loc[
            device_message.start : device_message.end - device_message.resolution
        ]

        # Get previous commitments
        commitments = self.commitments.copy()

        # Add requested commitment
        commitments.append(device_message.commitment)

        applicable_commitments = select_applicable(
            commitments, (device_message.start, device_message.end), slice=True
        )
        for c in applicable_commitments:
            print("EMS: Applicable commitments constants.values:{}".format(c.constants.values))
        print("EMS: Dev Curve Down: {}".format([c.deviation_cost_curve.gradient_down for c in applicable_commitments]))
        print("EMS: Dev Curve Up: {}\n".format([c.deviation_cost_curve.gradient_up for c in applicable_commitments]))

        scheduled_power_per_device, costs_per_commitment = device_scheduler(
            device_constraints=device_constraints,
            ems_constraints=ems_constraints,
            commitment_quantities=[
                commitment.constants for commitment in applicable_commitments
            ],
            commitment_downwards_deviation_price=[
                commitment.deviation_cost_curve.gradient_down
                for commitment in applicable_commitments
            ],
            commitment_upwards_deviation_price=[
                commitment.deviation_cost_curve.gradient_up
                for commitment in applicable_commitments
            ],
        )

        # Update flex data
        list_of_device_type_names = list(scheduled_power_per_device.keys())
        #TODO: further testing and then refactor
        if self.device_messages_cnt % 2 != 0:
            # Update prognosed_costs_over_horizons
            self.prognosed_costs_over_horizons[self.environment.now] = costs_per_commitment
            # Update prognosed_over_horizons table
            self.prognosed_over_horizons.loc[self.environment.now, "Generation"] = scheduled_power_per_device["Generation"].values
            self.prognosed_over_horizons.loc[self.environment.now, "Load"] = scheduled_power_per_device["Load"].values

            for idx in scheduled_power_per_device[list_of_device_type_names[0]].index:

                # Update prognosed_power_per_device table
                self.prognosed_power_per_device.loc[idx, "Generation"] = scheduled_power_per_device["Generation"][idx]
                self.prognosed_power_per_device.loc[idx, "Load"] = scheduled_power_per_device["Load"][idx]

                # Update planned_flex_per_device table
                gen_diff = self.prognosed_power_per_device.loc[idx, "Generation"] - self.planned_power_per_device.loc[idx, "Generation"]
                # print(gen_diff)
                if isnull(self.planned_flex_per_device.loc[idx, "Generation"]):
                    self.planned_flex_per_device.loc[idx, "Generation"] = gen_diff
                    # print ("g isnull")
                elif gen_diff > 0:
                    self.planned_flex_per_device.loc[idx, "Generation"] = self.planned_flex_per_device.loc[idx, "Generation"] + gen_diff
                    # print ("g diff > 0")
                elif gen_diff < 0:
                    self.planned_flex_per_device.loc[idx, "Generation"] = gen_diff + self.planned_flex_per_device.loc[idx, "Generation"]
                    # print ("g diff < 0")
                load_diff = self.prognosed_power_per_device.loc[idx, "Load"] - self.planned_power_per_device.loc[idx, "Load"]
                # print(load_diff)

                if isnull(self.planned_flex_per_device.loc[idx, "Load"]):
                    self.planned_flex_per_device.loc[idx, "Load"] = load_diff
                    # print ("isnull")
                elif load_diff > 0:
                    self.planned_flex_per_device.loc[idx, "Load"] = load_diff + self.planned_flex_per_device.loc[idx, "Load"]
                    # print ("load diff > 0")
                elif load_diff < 0:
                    self.planned_flex_per_device.loc[idx, "Load"] = self.planned_flex_per_device.loc[idx, "Load"] + load_diff
                    # print ("load diff < 0")

            print("EMS: Prognosed Power per Device: {} \n".format(scheduled_power_per_device))
            print("EMS: Prognosed Flex per Device: {} \n".format(self.planned_flex_per_device))
        else:
            # Update planned_costs_over_horizons table
            self.planned_costs_over_horizons[self.environment.now] = costs_per_commitment
            # Update planned_over_horizons table
            self.planned_over_horizons.loc[self.environment.now, "Generation"] = scheduled_power_per_device["Generation"].values
            self.planned_over_horizons.loc[self.environment.now, "Load"] = scheduled_power_per_device["Load"].values

            for idx in scheduled_power_per_device[list_of_device_type_names[0]].index:
                # Update planned_power_per_device table
                self.planned_power_per_device.loc[idx, "Generation"] = scheduled_power_per_device["Generation"][idx]
                self.planned_power_per_device.loc[idx, "Load"] = scheduled_power_per_device["Load"][idx]
                # Update planned_flex_per_device table
                gen_diff = (self.planned_power_per_device.loc[idx, "Generation"] - self.prognosed_power_per_device.loc[idx, "Generation"])
                # print(gen_diff)
                if isnull(self.planned_flex_per_device.loc[idx, "Generation"]):
                    self.planned_flex_per_device.loc[idx, "Generation"] = gen_diff
                    # print ("g isnull")
                elif gen_diff > 0:
                    self.planned_flex_per_device.loc[idx, "Generation"] = self.planned_flex_per_device.loc[idx, "Generation"] + gen_diff
                    # print ("g diff > 0")
                elif gen_diff < 0:
                    self.planned_flex_per_device.loc[idx, "Generation"] = gen_diff + self.planned_flex_per_device.loc[idx, "Generation"]
                    # print ("g diff < 0")

                load_diff = (self.planned_power_per_device.loc[idx, "Load"] - self.prognosed_power_per_device.loc[idx, "Load"])
                # print(load_diff)
                if isnull(self.planned_flex_per_device.loc[idx, "Load"]):
                    self.planned_flex_per_device.loc[idx, "Load"] = load_diff
                    # print ("isnull")
                elif load_diff > 0:
                    self.planned_flex_per_device.loc[idx, "Load"] = load_diff + self.planned_flex_per_device.loc[idx, "Load"]
                    # print ("load diff > 0")
                elif load_diff < 0:
                    self.planned_flex_per_device.loc[idx, "Load"] = self.planned_flex_per_device.loc[idx, "Load"] + load_diff
                    # print ("load diff < 0")

            print("EMS: Planned Power per Device: {} \n".format(scheduled_power_per_device))
            print("EMS: Planned Flex per Ddevice: {} \n".format(self.planned_flex_per_device))

        print("EMS: Planned Flex total: {} \n".format(self.planned_flex_per_device.sum().sum()))
        print("EMS: Prognosis profile costs: {} ".format(self.prognosed_costs_over_horizons[self.environment.now]))

        # Get the cost difference between prognosed baseline and planned flex-request-profile
        planned_costs = costs_per_commitment[0]
        prognosed_costs = self.prognosed_costs_over_horizons[self.environment.now][0]

        if prognosed_costs >= 0:
            if planned_costs >= 0:
                costs_of_requested_commitment = planned_costs - prognosed_costs
            elif planned_costs < 0:
                costs_of_requested_commitment = planned_costs + prognosed_costs
        elif prognosed_costs < 0:
                costs_of_requested_commitment = planned_costs - prognosed_costs

        planned_deviation_costs = sum(costs_per_commitment[1:])
        print("EMS: Planned deviation costs over horizon: {} ".format(planned_deviation_costs))
        # print("EMS: Cost Difference Prognosis - Request: {} ".format(sum(self.prognosed_costs_over_horizons[self.environment.now]) - costs_per_commitment[0]))
        print("EMS: Commitment costs over horizon: {} ".format(costs_per_commitment))
        print("EMS: Requested commitment costs: {} \n".format(costs_of_requested_commitment))
        # costs_of_requested_commitment = sum(costs_per_commitment)

        # Sum the planned power over all devices
        planned_values = array(
            [item for key,item in scheduled_power_per_device.items()]
        ).sum(axis=0)

        self.device_messages_cnt +=1
        #print("planned_values: {} ".format(planned_values))
        planned_power = initialize_series(
            data=planned_values,
            start=device_message.start,
            end=device_message.end,
            resolution=device_message.resolution,
        )

        return UdiEvent(
            id=self.environment.plan_board.get_message_id(),
            offered_values=planned_power,
            planned_flex=self.planned_flex_per_device.sum(axis=1),
            planned_deviation_costs=planned_deviation_costs,
            costs=costs_of_requested_commitment,
        )

    def get_device_message(
        self, device_message: Optional[DeviceMessage]
    ) -> Optional[DeviceMessage]:
        """Callback function to let the EMS get a DeviceMessage, if there is one."""
        return device_message

    def store_power(self):
        # for rounds in self.environment.plan_board.flexrequest_negotiation_log_1
        #     if self.environment.plan_board.flexrequest_negotiation_log_1
        # Update commitments due to realised power
        # Todo: base realised power on stochastic values
        # self.realised_power_per_device.loc[self.environment.now, "Load"] = self.planned_power_per_device.loc[self.environment.now, "Load"]
        # self.realised_power_per_device.loc[self.environment.now, "Generation"] = self.planned_power_per_device.loc[self.environment.now, "Generation"]

        return

    def step(self):

        # Store commitments
        self.store_power()
