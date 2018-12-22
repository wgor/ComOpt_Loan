from typing import List, Optional, Tuple, Union

from pandas import DataFrame, Series, isnull, IndexSlice, set_option
from numpy import array, nan, isnan, around

from warnings import simplefilter
simplefilter(action='ignore', category=FutureWarning)

from comopt.data_structures.commitments import (
    DeviationCostCurve,
    PiecewiseConstantProfileCommitment as Commitment,
)
from comopt.data_structures.usef_message_types import DeviceMessage, UdiEvent
from comopt.data_structures.utils import select_applicable
from comopt.model.utils import initialize_df, initialize_series, initialize_index, create_multi_index_log

from comopt.solver.ems_solver import device_scheduler
from comopt.utils import Agent
from comopt.model.utils import (
    select_prognosis_or_planned_prefix,
    store_prices_per_device,
    store_contract_costs_per_device,
    store_flexibility_per_device,

    store_requested_power_per_datetime,
    store_requested_flex_per_datetime,
    store_power_per_datetime,
    store_flexibility_per_datetime,
    store_contract_costs_per_datetime,
    store_deviation_costs_per_datetime,
    store_flex_costs_per_datetime,
    store_commitment_costs_per_datetime,
    store_realised_and_commited_values
)


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
        flex_price: float,
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
        self.flex_price = flex_price
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
                      "Prog flexibility", "Plan flexibility", "Real flexibility", \
                      "Prog contract costs", "Plan contract costs", "Real contract costs", \
                      # "Prog deviation costs", "Plan deviation costs", "Real deviation costs", \
                      # "Prog total costs", "Plan total costs", "Real total costs", \
                      ]

        # Stores data per device and datetime [first_index: datetime, second_index: devices]
        self.device_data = create_multi_index_log(
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
                  "Prog commitment costs", "Plan commitment costs", "Real commitment costs", \
                  "Purchase price", "Feedin price", "Dev price up", "Dev price down", \
                  ]

        # Stores aggregated device data per datetime
        self.ems_data = initialize_df(
            columns_ems_data, environment.start, environment.end, environment.resolution
        )

        second_index_horizon_data = [x for x in self.device_types]
        second_index_horizon_data.extend(["Total Costs", "Flexibility"])
        self.horizon_data = create_multi_index_log(
            first_index=self.commitments[0].constants.index,
            second_index=second_index_horizon_data,
            index_names=["Datetime", "Target"],
            column_names=["Prog", "Plan"])

        self.get_initial_device_schedule()

        # self.horizon_data.set_index('Costs',append=True, inplace=True)

    def get_initial_device_schedule(self):

        device_constraints = [
            device_constraints.loc[
                self.environment.datetime_index
            ]
            for device_constraints in self.device_constraints
        ]
        ems_constraints = self.ems_constraints.loc[
            self.environment.datetime_index
        ]

        # Get previous commitments
        commitments = self.commitments.copy()

        # applicable_commitments = select_applicable(
        #     commitments, (self.environment.datetime_index[0],self.environment.datetime_index[-1]), slice=True
        # )

        scheduled_power_per_device, costs_per_commitment = device_scheduler(
            device_constraints=device_constraints,
            ems_constraints=ems_constraints,
            commitment_quantities=[
                commitment.constants for commitment in commitments
            ],
            commitment_downwards_deviation_price=[
                commitment.deviation_cost_curve.gradient_down
                for commitment in commitments
            ],
            commitment_upwards_deviation_price=[
                commitment.deviation_cost_curve.gradient_up
                for commitment in commitments
            ],
        )


        print(scheduled_power_per_device)

        # print(düster)
        return


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

        print("------------AT SOLVER------------")
        data = self.store_data(device_message=device_message,
                               targeted_power_per_device=scheduled_power_per_device,
                               costs_per_commitment=costs_per_commitment,
                               commitments=applicable_commitments)

        # self.device_messages_cnt += 1
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
            offered_flexibility=data["EMS flexibility"],
            contract_costs=data["EMS contract costs"],
            deviation_costs=data["EMS deviation costs"],
            deviation_cost_curve=device_message.commitment.deviation_cost_curve,
            costs=data["EMS commitment costs"]
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

        ''' Data storing during post_udi_event function call:

            Data input: Solver output after optimization (targeted_power_per_device,costs_per_commitment) gets used
            Data to save: Prognosed values[Prognosis] and planned values [Flexrequest].
            Device message type: "Request"

            Data storing after flexrequest negotiations:

            Data input: Device message values derived from offer and negotiation output gets used
            Data to save: Realised and commited values.
            Device message type: "Order"

        '''
        # Only needed for data storing during post_udi_event function cal
        try:
            start = targeted_power_per_device[0].index[0]
            end = targeted_power_per_device[0].index[-1]

        except:
            pass

        # 1) STORE PRGOGNOSIS AND PLANNED VALUES
        # Assign a prefix to distinguish between Prognosis and Planned UDI-Event
        if "Request" in device_message.type:

            prefix = select_prognosis_or_planned_prefix(self,
                                                        device_message=device_message)

        # 2) STORE ORDER VALUES
        # Store commited data and commitments:
        elif "Order" in device_message.type:

            store_realised_and_commited_values(self,
                                               commitment=commitments,
                                               device_message=device_message)


            # Store commitment only if a negotiation got cleared
            if "Succeeded Negotiation" in device_message.description:

                self.commitments.append(Commitment(label=None,
                                                   constants=device_message.commitment.constants,
                                                   costs=device_message.costs,
                                                   deviation_cost_curve=device_message.commitment.deviation_cost_curve,
                                                   flow_unit_multiplier=1) # keep 1 as value here
                                        )
            return

        #-------------------- PRICE data ---------------------#
        store_prices_per_device(self, commitments=commitments,)


        #-------------------- DEVICE data --------------------#
        for enum, device in enumerate(self.device_types):

            for index, row in targeted_power_per_device[0].iteritems():

                # POWER per device: Derived from solver output
                self.device_data.loc[(index, device), str(prefix + "power")] = targeted_power_per_device[enum][index]

                # FLEXIBILITY per device
                flexibility_per_device = store_flexibility_per_device(
                                                        self,
                                                        prefix=prefix,
                                                        enum=enum,
                                                        index=index,
                                                        targeted_power_per_device=targeted_power_per_device,
                                                        commitments=commitments,
                                                        device=device
                                                    )

                # CONTRACT COSTS per device
                contract_costs_per_device = store_contract_costs_per_device(
                                                        self,
                                                        prefix=prefix,
                                                        enum=enum,
                                                        index=index,
                                                        targeted_power_per_device=targeted_power_per_device,
                                                        device=device
                                                    )

        #---------------------- EMS data --------------------#
        for index, row in targeted_power_per_device[0].iteritems():

            # REQUESTED POWER: Derived from commitment
            requested_power  = store_requested_power_per_datetime(
                                                        self,
                                                        index=index,
                                                        prefix=prefix,
                                                        commitments=commitments)

            # REQUESTED FLEX: Derived from commitment
            requested_flexibility = store_requested_flex_per_datetime(
                                                        self,
                                                        index=index,
                                                        prefix=prefix,
                                                        device_message=device_message)


            # POWER over all devices for current timestep
            power_over_all_devices = store_power_per_datetime(
                                                        self,
                                                        index=index,
                                                        prefix=prefix)

            # FLEXBILITY over all devices for current timestep
            flexibility_over_all_devices = store_flexibility_per_datetime(
                                                        self,
                                                        index=index,
                                                        prefix=prefix)

            # CONTRACT COSTS over all devices for current timestep
            contract_costs_over_all_devices = store_contract_costs_per_datetime(
                                                        self,
                                                        index=index,
                                                        prefix=prefix,
                                                        power_over_all_devices=power_over_all_devices)

            # DEVIATION COSTS over all devices for one timestep
            deviation_costs_over_all_devices = store_deviation_costs_per_datetime(
                                                        self,
                                                        index=index,
                                                        prefix=prefix,
                                                        power_over_all_devices=power_over_all_devices,
                                                        requested_power=requested_power)

            # FLEX COSTS: flexibility_over_all_devices * flex_price
            flex_costs_over_all_devices = store_flex_costs_per_datetime(
                                                        self,
                                                        index=index,
                                                        prefix=prefix,
                                                        flexibility_over_all_devices=flexibility_over_all_devices)

            # COMMTMENT COSTS: flex_costs_over_all_devices +
            commitment_costs_over_all_devices = store_commitment_costs_per_datetime(
                                                                        self,
                                                                        index=index,
                                                                        prefix=prefix,
                                                                        flex_costs_over_all_devices=flex_costs_over_all_devices,
                                                                        deviation_costs_over_all_devices=deviation_costs_over_all_devices)

        #         #-------------------- HORIZON data --------------------#
        #         # Prognosed POWER horizon: Stores the prognosed power values over the actual horizon as a list per device.
        #         self.horizon_data.loc[(self.environment.now, device), "Prog"] = targeted_power_per_device[enum].values
        #
        # # Prognosed COSTS horizon: Values for each datetime of the actual horizon, stored as a list per device.
        # self.horizon_data.loc[(self.environment.now, "Total Costs"), "Prog"] = costs_per_commitment
        #
        # # Prognosed FLEX horizon: Values for each datetime of the actual horizon, stored as a list per device.
        # self.horizon_data.loc[(self.environment.now, "Flexibility"), "Prog"] = self.device_data.loc[IndexSlice[self.environment.now, :], "Prog flexibility"].sum(axis=0)

        #-------------------- PRINTS --------------------#
        for c in commitments:
            print("EMS: Applicable commitments constants.values: {}".format(c.constants.values))

        # print("\nDEVICE: Contract costs: {}\n".format(self.device_data.loc[:, str(prefix + "contract costs")]))
        # print("\nDEVICE: Flex: {}\n".format(self.device_data.loc[:, str(prefix + "flexibility")]))

        print("EMS: Targeted Flex: {}\n".format(list(device_message.targeted_flexibility.values)))
        print("EMS: Dev Curve Down: {}".format([c.deviation_cost_curve.gradient_down for c in commitments]))
        print("EMS: Dev Curve Up: {}".format([c.deviation_cost_curve.gradient_up for c in commitments]))

        print("\nEMS: Costs per commitment:{}".format(costs_per_commitment))

        print("\n Power over all: {}".format(self.ems_data.loc[start:end, str(prefix + "power")]))
        # print("\n Flex over all: {}".format(self.ems_data.loc[start:end, "flexibility"]))
        # print("\n CC over all: {}".format(self.ems_data.loc[start:end, "contract costs"]))
        # print("\n Dev costs over all: {}".format(self.ems_data.loc[start:end, "dev costs"]))
        # print("\n Tot costs over all: {}".format(self.ems_data.loc[start:end, "total costs"]))
        # print("\n Com costs over all: {}".format(self.ems_data.loc[start:end, "commitment costs"]))

        return {"EMS power": around(self.ems_data.loc[start:end, str(prefix + "power")].astype("float64"),3), \
                "EMS flexibility": around(self.ems_data.loc[start:end, str(prefix +"flexibility")].astype("float64"),3), \
                "EMS contract costs": around(self.ems_data.loc[start:end, str(prefix +"contract costs")].astype("float64"),3), \
                "EMS deviation costs": around(self.ems_data.loc[start:end, str(prefix +"dev costs")].astype("float64"),3), \
                "EMS flex costs": around(self.ems_data.loc[start:end, str(prefix +"flex costs")].astype("float64"),3), \
                "EMS commitment costs": around(self.ems_data.loc[start:end, str(prefix +"commitment costs")].astype("float64"),3)}


    def step(self):
        return
