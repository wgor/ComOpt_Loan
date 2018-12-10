from typing import List, Optional, Tuple

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
        self.device_messages = initialize_series(
            start=self.environment.start,
            end=self.environment.end,
            resolution=self.environment.resolution,
            data=0,
        )

        # Stores data per device and datetime
        self.device_data = create_data_log(
            first_index=self.commitments[0].constants.index,
            second_index=self.device_types,
            index_names=["Datetime", "Device"],
            column_names=[
                          "Prog power", "Plan power", "Real power", "Dev power",\
                          "Prog flexibility", "Plan flexibility", "Realised flexibility", "Deviated flexibility", \
                          "Prog contract costs", "Plan contract costs", "Realised contract costs", \
                          "Prog deviation costs", "Plan deviation costs", "Realised deviation costs", \
                          "Prog total costs", "Plan total costs", "Realised total costs", \
                          ])

        # Stores aggregated device data per datetime
        self.ems_data = DataFrame(
            index=["Datetime"],
            columns=[
                      "Requested power", "Requested flexibility",
                      "Prog power", "Plan power", "Realised power", "Deviated power",\
                      "Prog flexibility", "Plan flexibility", "Realised flexibility", "Deviated flexibility", \
                      "Prog contract costs", "Plan contract costs", "Realised contract costs", \
                      "Prog deviation costs", "Plan deviation costs", "Realised deviation costs", \
                      "Prog total costs", "Plan total costs", "Realised total costs", \
                      "Plan commitment costs", "Realised commitment costs", \
                      "Purchase price", "Feedin price", "Deviation price up", "Deviation price down", \
                      ])

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

        data = self.store_data(scheduled_power_per_device=scheduled_power_per_device,
                               targeted_flexibility=device_message.targeted_flexibility,
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
            offered_flexibility=data["flexibility"],
            contract_costs=data["contract costs"],
            deviation_costs=data["deviation costs"],
            costs=data["commitment costs"]
        )

    def get_device_message(
        self, device_message: Optional[DeviceMessage]
    ) -> Optional[DeviceMessage]:
        """Callback function to let the EMS get a DeviceMessage, if there is one."""
        return device_message

    def store_data(self,
                   scheduled_power_per_device: Series,
                   targeted_flexibility: Series,
                   costs_per_commitment: List,
                   commitments: List) -> Tuple:

        ## PRICE data
        # Deviation prices
        self.ems_data.loc[self.environment.now, "Deviation price up"] = commitments[-1].deviation_cost_curve.gradient_up
        self.ems_data.loc[self.environment.now, "Deviation price down"] = commitments[-1].deviation_cost_curve.gradient_down

        # Contract Prices: self.ems_prices could be adapted for dynamic price schemes (e.g. using a Series)
        self.ems_data.loc[self.environment.now, "Feedin price"] = commitments[0].deviation_cost_curve.gradient_down
        self.ems_data.loc[self.environment.now, "Purchase price"] = commitments[0].deviation_cost_curve.gradient_up

        # Assign a Prefix to distinguish between Prognosis and Flexrequest UDI-Events
        Prefix = ""
        if self.device_messages_cnt % 2 != 0:
            Prefix = "Prog "
        else:
            Prefix = "Plan "

        #-------------------- DEVICE data --------------------#
        for enum, device in enumerate(self.device_types):

            for idx in scheduled_power_per_device[0].index:

                # POWER per device
                self.device_data.loc[(idx, device), str(Prefix + "power")
                ] = scheduled_power_per_device[enum][idx]

                # CONTRACT COSTS per device
                if scheduled_power_per_device[enum][idx] >= 0:
                    self.device_data.loc[(idx, device), str(Prefix + "contract costs")
                    ] = scheduled_power_per_device[enum][idx] * self.ems_data.loc[self.environment.now, "Purchase price"]

                else:
                    self.device_data.loc[(idx, device), str(Prefix + "contract costs")
                    ] = scheduled_power_per_device[enum][idx] * self.ems_data.loc[self.environment.now, "Feedin price"]

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
                if isnull(self.device_data.loc[(idx, device), str(Prefix + "deviation costs")]) == True:

                    self.device_data.loc[(idx, device), str(Prefix + "total costs")] = self.device_data.loc[(idx, device), str(Prefix + "contract costs")]

                else:
                    self.device_data.loc[(idx, device), str(Prefix + "total costs")] = self.device_data.loc[(idx, device), str(Prefix + "contract costs")] \
                                                                                       + self.device_data.loc[(idx, device), str(Prefix + "deviation costs")]

                #-------------------- EMS data --------------------#
                # REQUESTED POWER
                self.ems_data.loc[idx, "Requested power"] = commitments[-1].constants.loc[idx]

                # REQUESTED FLEX
                self.ems_data.loc[idx, "Requested flexibility"] = targeted_flexibility.loc[idx]

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
                if self.ems_data.loc[idx, str(Prefix + "power")] > self.ems_data.loc[idx, "Requested power"]:

                    self.ems_data.loc[idx, str(Prefix + "deviation costs")] = (self.ems_data.loc[idx, str(Prefix + "power")] - self.ems_data.loc[idx, "Requested power"]) \
                                                                              * self.ems_data.loc[self.environment.now, "Deviation price up"]
                else:
                    self.ems_data.loc[idx, str(Prefix + "deviation costs")] = (self.ems_data.loc[idx, "Requested power"] - self.ems_data.loc[idx, str(Prefix + "power")]) \
                                                                              * self.ems_data.loc[self.environment.now, "Deviation price down"]

                # TOTAL COSTS over all devices
                if isnull(self.ems_data.loc[idx, str(Prefix + "deviation costs")]) == True:

                    self.ems_data.loc[idx, str(Prefix + "total costs")] = self.ems_data.loc[idx, str(Prefix + "contract costs")]

                else:
                    self.ems_data.loc[idx, str(Prefix + "total costs")] = self.ems_data.loc[idx, str(Prefix + "contract costs")] \
                                                                          + self.ems_data.loc[idx, str(Prefix + "deviation costs")]

                # COMMTMENT COSTS: Difference between prognosed and planned costs
                if self.ems_data.loc[idx, "Prog total costs"] > self.ems_data.loc[idx, "Plan total costs"]:

                    self.ems_data.loc[idx, str(Prefix + "commitment costs")] = self.ems_data.loc[idx, "Prog total costs"] - self.ems_data.loc[idx, "Plan total costs"]
                else:
                    self.ems_data.loc[idx, str(Prefix + "commitment costs")] = self.ems_data.loc[idx, "Plan total costs"] - self.ems_data.loc[idx, "Prog total costs"]

                #-------------------- HORIZON data --------------------#
                # Prognosed POWER horizon: Stores the prognosed power values over the actual horizon as a list per device.
                self.horizon_data.loc[(self.environment.now, device), "Prog"] = scheduled_power_per_device[enum].values

        # Prognosed COSTS horizon: Values for each datetime of the actual horizon, stored as a list per device.
        self.horizon_data.loc[(self.environment.now, "Total Costs"), "Prog"] = costs_per_commitment

        # Prognosed FLEX horizon: Values for each datetime of the actual horizon, stored as a list per device.
        self.horizon_data.loc[(self.environment.now, "Flexibility"), "Prog"] = self.device_data.loc[IndexSlice[self.environment.now, :], "Prog flexibility"].sum(axis=0)

        #-------------------- PRINTS --------------------#
        for c in commitments:
            print("EMS: Applicable commitments constants.values: {}".format(c.constants.values))

        print("EMS: Targeted Flex: {}\n".format(list(targeted_flexibility.values)))
        print("EMS: Dev Curve Down: {}".format([c.deviation_cost_curve.gradient_down for c in commitments]))
        print("EMS: Dev Curve Up: {}".format([c.deviation_cost_curve.gradient_up for c in commitments]))

        print("\nEMS: Costs per commitment:{}".format(costs_per_commitment))
        print("\nEMS: Scheduled power:\n{}".format(scheduled_power_per_device))

        print("\nDEVICE: " + Prefix + "data:\n{}".format(self.device_data.loc[:, [str(Prefix + "power"), str(Prefix + "flexibility"), \
                                                                                  str(Prefix + "contract costs"), str(Prefix + "deviation costs"), \
                                                                                  str(Prefix + "total costs"),]]))

        print("\nEMS: " + Prefix + "data:\n{}".format(self.ems_data.loc[:, ["Requested power", str(Prefix + "power"), \
                                                                            "Requested flexibility", str(Prefix + "flexibility"), \
                                                                            str(Prefix + "contract costs"), str(Prefix + "deviation costs"), \
                                                                            str(Prefix + "total costs"), str(Prefix + "commitment costs")]]))

        return {"values": self.ems_data.loc[:, str(Prefix + "power")], \
                "flexibility": self.ems_data.loc[:, str(Prefix + "flexibility")], \
                "contract costs": self.ems_data.loc[:, str(Prefix + "contract costs")], \
                "deviation costs": self.ems_data.loc[:, str(Prefix + "deviation costs")], \
                "total costs": self.ems_data.loc[:, str(Prefix + "total costs")], \
                "commitment costs": self.ems_data.loc[:, str(Prefix + "commitment costs")]}

    def step(self):

        # Store commitments
        self.store_power()
