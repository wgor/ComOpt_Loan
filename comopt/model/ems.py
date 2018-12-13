from typing import List, Optional, Tuple, Union

from pandas import DataFrame, Series, isnull, IndexSlice, set_option
from numpy import array, nan, isnan

from warnings import simplefilter
simplefilter(action='ignore', category=FutureWarning)

from comopt.data_structures.commitments import (
    DeviationCostCurve,
    PiecewiseConstantProfileCommitment as Commitment,
)
from comopt.data_structures.usef_message_types import DeviceMessage, UdiEvent
from comopt.data_structures.utils import select_applicable
from comopt.model.utils import initialize_df, initialize_series, initialize_index, create_data_log

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

        # TODO: Loop and refactor
        # TODO: use planboard messages instead of instance variable
        self.device_messages = initialize_df(
            columns=["Prognosis", "Request", "Order"],
            start=self.environment.start,
            end=self.environment.end,
            resolution=self.environment.resolution,)

        # Abbreviations: "Prog":Prognosis, "Plan":Planned, "Real":Realised, "Com":Commited, "Dev":Deviation
        columns_device_data=[
                      "Prog power", "Plan power", "Real power", "Dev power",\
                      "Prog flexibility", "Plan flexibility", "Real flexibility", "Dev flexibility", \
                      "Prog contract costs", "Plan contract costs", "Real contract costs", \
                      "Prog dev costs", "Plan dev costs", "Real dev costs", \
                      "Prog total costs", "Plan total costs", "Real total costs", \
                      ]

        # Stores data per device and datetime
        self.device_data = create_data_log(
            first_index=self.commitments[0].constants.index,
            second_index=self.device_types,
            index_names=["Datetime", "Device"],
            column_names=columns_device_data
            )
        # Abbreviations: "Prog" = Prognosis, "Plan" = Planned, "Real" = Realised, "Dev"= Deviation
        columns_ems_data=[
                  "Req power", "Req flexibility",
                  "Prog power", "Plan power", "Com power", "Real power", "Dev power",\
                  "Prog flexibility", "Plan flexibility", "Com flexibility", "Real flexibility", "Dev flexibility", \
                  "Prog contract costs", "Plan contract costs", "Real contract costs", \
                  "Prog dev costs", "Plan dev costs", "Real dev costs", \
                  "Prog total costs", "Plan total costs", "Real total costs", \
                  "Plan commitment costs", "Real commitment costs", \
                  "Purchase price", "Feedin price", "Dev price up", "Dev price down", \
                  ]

        # Stores aggregated device data per datetime
        self.ems_data = initialize_df(
            columns_ems_data, environment.start, environment.end, environment.resolution
        )

        second_index_horizon_data = [x for x in self.device_types]
        second_index_horizon_data.extend(["Total Costs", "Flexibility"])
        self.horizon_data = create_data_log(
            first_index=self.commitments[0].constants.index,
            second_index=second_index_horizon_data,
            index_names=["Datetime", "Target"],
            column_names=["Prog", "Plan"])

        # self.horizon_data.set_index('Costs',append=True, inplace=True)

    def post_udi_event(self, device_message: DeviceMessage) -> UdiEvent:
        """Callback function to have the EMS create and post a UdiEvent."""

        # TODO: use planboard messages instead of instance variable
        # self.device_messages.loc[device_message.start] = device_message

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

        data = self.store_data(device_message=device_message,
                               targeted_power_per_device=scheduled_power_per_device,
                               costs_per_commitment=costs_per_commitment,
                               commitments=applicable_commitments)

        self.device_messages_cnt += 1
        # Sum the planned power over all devices
        offered_power = initialize_series(
            data=array([power for power in scheduled_power_per_device]).sum(axis=0),
            start=device_message.start,
            end=device_message.end,
            resolution=device_message.resolution,
        )

        return UdiEvent(
            id=self.environment.plan_board.get_message_id(),
            offered_values=offered_power,
            offered_flexibility=data["Flexibility"],
            contract_costs=data["Contract costs"],
            deviation_costs=data["Deviation costs"],
            costs=data["Commitment costs"]
        )

    def get_device_message(
        self, device_message: Optional[DeviceMessage]
    ) -> Optional[DeviceMessage]:
        """Callback function to let the EMS get a DeviceMessage, if there is one."""
        return device_message

    def store_data(self,
                   commitments: Union[List, Commitment],
                   device_message: DeviceMessage,
                   targeted_power_per_device: Union[None,Series] = None,
                   costs_per_commitment: Union[None,List] = None) -> Tuple:


        # Store commited data and commitments:

        if "Order" in device_message.description:

            self.device_messages.loc[self.environment.now, "Order"] = device_message

            # If device message description is "Order" and the device message targeted flex values are equal to the prognosed flex values,
            # then the negotiation didn't get cleared. Hence use the prognosed values to assign the "commited" columns.
            # Otherwise use the planned values.
            for idx in device_message.targeted_flexibility.index:

                # Negotiation failed
                if device_message.targeted_flexibility.loc[idx] == self.ems_data.loc[idx, "Prog flexibility"]:

                    self.ems_data.loc[idx, "Com power"] = self.ems_data.loc[idx, "Prog power"]
                    self.ems_data.loc[idx, "Com flexibility"] = self.ems_data.loc[idx, "Prog flexibility"]

                    # if device_message.targeted_flexibility.loc[idx] is device_message.targeted_flexibility.index[-1]:
                    #     self.store_commitments(commitment=None)

                else:

                # Negotiation succeeded
                    self.ems_data.loc[idx, "Com power"] = self.ems_data.loc[idx, "Plan power"]
                    self.ems_data.loc[idx, "Com power"] = self.ems_data.loc[idx, "Plan power"]

                    # Store commitment
                    # Commitments only get stored if a negotiation got cleared.
                    if device_message.targeted_flexibility.loc[idx] is device_message.targeted_flexibility.index[-1]:
                        self.store_commitments(commitment=Commitments)

            return

        elif "Request" in device_message.description:

            if isnull(self.device_messages.loc[self.environment.now, "Prognosis"]) == True:

                self.device_messages.loc[self.environment.now, "Prognosis"] = device_message
                Prefix = "Prog "

            else:
                self.device_messages.loc[self.environment.now, "Request"] = device_message
                Prefix = "Plan "

        ## PRICE data
        # Deviation prices
        self.ems_data.loc[self.environment.now, "Deviation price up"] = commitments[-1].deviation_cost_curve.gradient_up
        self.ems_data.loc[self.environment.now, "Deviation price down"] = commitments[-1].deviation_cost_curve.gradient_down

        # Contract Prices: self.ems_prices could be adapted for dynamic price schemes (e.g. using a Series)
        self.ems_data.loc[self.environment.now, "Feedin price"] = commitments[0].deviation_cost_curve.gradient_down
        self.ems_data.loc[self.environment.now, "Purchase price"] = commitments[0].deviation_cost_curve.gradient_up

        #-------------------- DEVICE data --------------------#
        for enum, device in enumerate(self.device_types):

            for idx in targeted_power_per_device[0].index:

                # POWER per device
                self.device_data.loc[(idx, device), str(Prefix + "power")
                ] = targeted_power_per_device[enum][idx]

                # CONTRACT COSTS per device
                if targeted_power_per_device[enum][idx] >= 0:
                    self.device_data.loc[(idx, device), str(Prefix + "contract costs")
                    ] = targeted_power_per_device[enum][idx] * self.ems_data.loc[self.environment.now, "Purchase price"]

                else:
                    self.device_data.loc[(idx, device), str(Prefix + "contract costs")
                    ] = targeted_power_per_device[enum][idx] * self.ems_data.loc[self.environment.now, "Feedin price"]

                # FLEXIBILITY per device
                if self.device_data.loc[(idx, device), "Prog power"] > self.device_data.loc[(idx, device), "Plan power"]:
                    diff = (self.device_data.loc[(idx, device), "Prog power"] - self.device_data.loc[(idx, device), "Plan power"])

                    # DEVIATION COSTS per device if deviation UP occurs
                    # self.device_data.loc[(idx, device), str(Prefix + "deviation costs")
                    # ] = diff * self.ems_data.loc[self.environment.now, "Deviation price up"]

                else:
                    diff = (self.device_data.loc[(idx, device), "Plan power"] - self.device_data.loc[(idx, device), "Prog power"])

                    #DEVIATION COSTS per device if deviation DOWN occurs
                    #TODO: Check if -1 holds for all constellations
                    # self.device_data.loc[(idx, device), str(Prefix + "deviation costs")
                    # ] = diff * self.ems_data.loc[self.environment.now, "Deviation price down"] *-1

                self.device_data.loc[(idx, device), str(Prefix + "flexibility")] = diff

                # TOTAL COSTS per device
                if isnull(self.device_data.loc[(idx, device), str(Prefix + "dev costs")]) == True:

                    self.device_data.loc[(idx, device), str(Prefix + "total costs")] = self.device_data.loc[(idx, device), str(Prefix + "contract costs")]

                else:
                    self.device_data.loc[(idx, device), str(Prefix + "total costs")] = self.device_data.loc[(idx, device), str(Prefix + "contract costs")] \
                                                                                       + self.device_data.loc[(idx, device), str(Prefix + "dev costs")]

                #-------------------- EMS data --------------------#
                # REQUESTED POWER
                self.ems_data.loc[idx, "Req power"] = commitments[-1].constants.loc[idx]

                # REQUESTED FLEX
                self.ems_data.loc[idx, "Req flexibility"] = device_message.targeted_flexibility.loc[idx]

                # POWER over all devices
                self.ems_data.loc[idx, str(Prefix + "power")] = self.device_data.loc[IndexSlice[idx,:], str(Prefix + "power")].sum()

                # FLEXBILITY over all devices
                self.ems_data.loc[idx, str(Prefix + "flexibility")] = self.device_data.loc[IndexSlice[idx,:], str(Prefix + "flexibility")].sum()

                # CONTRACT COSTS over all devices
                if self.ems_data.loc[idx, str(Prefix + "power")] >= 0:

                    self.ems_data.loc[idx, str(Prefix + "contract costs")] = self.ems_data.loc[idx, str(Prefix + "power")] \
                                                                             * self.ems_data.loc[self.environment.now, "Purchase price"]
                else:
                    self.ems_data.loc[idx, str(Prefix + "contract costs")] = self.ems_data.loc[idx, str(Prefix + "power")] \
                                                                             * self.ems_data.loc[self.environment.now, "Feedin price"]

                # DEVIATION COSTS over all devices
                if self.ems_data.loc[idx, str(Prefix + "power")] > self.ems_data.loc[idx, "Req power"]:

                    self.ems_data.loc[idx, str(Prefix + "dev costs")] = (self.ems_data.loc[idx, str(Prefix + "power")] \
                                                                        - self.ems_data.loc[idx, "Req power"]) \
                                                                        * self.ems_data.loc[self.environment.now, "Dev price up"]
                else:
                    self.ems_data.loc[idx, str(Prefix + "dev costs")] = (self.ems_data.loc[idx, "Req power"]
                                                                        - self.ems_data.loc[idx, str(Prefix + "power")]) \
                                                                        * self.ems_data.loc[self.environment.now, "Dev price down"]

                # TOTAL COSTS over all devices
                if isnull(self.ems_data.loc[idx, str(Prefix + "dev costs")]) == True:

                    self.ems_data.loc[idx, str(Prefix + "total costs")] = self.ems_data.loc[idx, str(Prefix + "contract costs")]

                else:
                    self.ems_data.loc[idx, str(Prefix + "total costs")] = self.ems_data.loc[idx, str(Prefix + "contract costs")] \
                                                                          + self.ems_data.loc[idx, str(Prefix + "dev costs")]

                # COMMTMENT COSTS: Difference between prognosed and planned costs
                if self.ems_data.loc[idx, "Prog total costs"] > self.ems_data.loc[idx, "Plan total costs"]:

                    self.ems_data.loc[idx, str(Prefix + "commitment costs")] = self.ems_data.loc[idx, "Prog total costs"] - self.ems_data.loc[idx, "Plan total costs"]
                else:
                    self.ems_data.loc[idx, str(Prefix + "commitment costs")] = self.ems_data.loc[idx, "Plan total costs"] - self.ems_data.loc[idx, "Prog total costs"]

                #-------------------- HORIZON data --------------------#
                # Prognosed POWER horizon: Stores the prognosed power values over the actual horizon as a list per device.
                self.horizon_data.loc[(self.environment.now, device), "Prog"] = targeted_power_per_device[enum].values

        # Prognosed COSTS horizon: Values for each datetime of the actual horizon, stored as a list per device.
        self.horizon_data.loc[(self.environment.now, "Total Costs"), "Prog"] = costs_per_commitment

        # Prognosed FLEX horizon: Values for each datetime of the actual horizon, stored as a list per device.
        self.horizon_data.loc[(self.environment.now, "Flexibility"), "Prog"] = self.device_data.loc[IndexSlice[self.environment.now, :], "Prog flexibility"].sum(axis=0)

        #-------------------- PRINTS --------------------#
        for c in commitments:
            print("EMS: Applicable commitments constants.values: {}".format(c.constants.values))

        print("EMS: Targeted Flex: {}\n".format(list(device_message.targeted_flexibility.values)))
        print("EMS: Dev Curve Down: {}".format([c.deviation_cost_curve.gradient_down for c in commitments]))
        print("EMS: Dev Curve Up: {}".format([c.deviation_cost_curve.gradient_up for c in commitments]))

        print("\nEMS: Costs per commitment:{}".format(costs_per_commitment))
        print("\nEMS: Scheduled power:\n{}".format(targeted_power_per_device))

        print("\nDEVICE: " + Prefix + "data:\n{}".format(self.device_data.loc[:, [str(Prefix + "power"), str(Prefix + "flexibility"), \
                                                                                  str(Prefix + "contract costs"), str(Prefix + "dev costs"), \
                                                                                  str(Prefix + "total costs"),]]))

        print("\nEMS: " + Prefix + "data:\n{}".format(self.ems_data.loc[:, ["Req power", str(Prefix + "power"), \
                                                                            "Req flexibility", str(Prefix + "flexibility"), \
                                                                            str(Prefix + "contract costs"), str(Prefix + "dev costs"), \
                                                                            str(Prefix + "total costs"), str(Prefix + "commitment costs")]]))

        return {"Values": self.ems_data.loc[:, str(Prefix + "power")], \
                "Flexibility": self.ems_data.loc[:, str(Prefix + "flexibility")], \
                "Contract costs": self.ems_data.loc[:, str(Prefix + "contract costs")], \
                "Deviation costs": self.ems_data.loc[:, str(Prefix + "dev costs")], \
                "Total costs": self.ems_data.loc[:, str(Prefix + "total costs")], \
                "Commitment costs": self.ems_data.loc[:, str(Prefix + "commitment costs")]}

    def store_commitments(self,commitment: Commitment = None):

        if commitment.deviation_cost_curve is None:

            gradient_down = 0
            gradient_up = 0

        else:

            gradient_down = commitment.deviation_cost_curve.gradient_down
            gradient_up = commitment.deviation_cost_curve.gradient_up

        self.commitments.append(Commitment(label=None,
                                           constants=commitment.constants,
                                           costs=commitment.costs,
                                           deviation_cost_curve=DeviationCostCurve(
                                           gradient=(gradient_down, gradient_up),
                                            # keep 1 as value here
                                           flow_unit_multiplier=1,
                                                )
                                            )
                                )
        # else:
        #     self.commitments.append(Commitment(label=None,
        #                                        constants=initialize_series(data=nan, start),
        #                                        costs=nan,
        #                                        deviation_cost_curve=DeviationCostCurve(
        #                                        gradient=(0, 0),
        #                                         # keep 1 as value here
        #                                        flow_unit_multiplier=1,
        #                                             )
        #                                         )
        #                             )

        return

    def step(self):
        return
        # Store commitments
        # self.store_power()
