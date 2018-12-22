from typing import List, Optional, Union, Callable, Tuple
from datetime import date, datetime, timedelta

from pandas import DataFrame, DatetimeIndex, Series, MultiIndex, Index, isnull, IndexSlice, to_numeric
from pandas.tseries.frequencies import to_offset

from numpy import ndarray, nan, nan_to_num


def initialize_df(
    columns: List[str], start: datetime, end: datetime, resolution: timedelta
) -> DataFrame:
    df = DataFrame(index=initialize_index(start, end, resolution), columns=columns)
    return df


def initialize_series(
    data: Optional[Union[Series, List[float], ndarray, float]],
    start: datetime,
    end: datetime,
    resolution: timedelta,
) -> Series:
    s = Series(index=initialize_index(start, end, resolution), data=data)
    return s


def initialize_index(
    start: Union[date, datetime], end: Union[date, datetime], resolution: timedelta
) -> Series:
    i = DatetimeIndex(
        start=start, end=end, freq=to_offset(resolution), closed="left", name="datetime"
    )
    return i


def create_multi_index_log(
    first_index: Union[List, Index],
    second_index: Union[List, Index],
    index_names: List,
    column_names: List) -> DataFrame:

    """ Returns a multiindex dataframe with inidices (datetime, rounds) and columns for prices, bids, profits, etc. """

    logfile = DataFrame(
        index=MultiIndex.from_product(
            iterables=[
                first_index,
                second_index,
            ],
            names=index_names,
        ),
        columns=column_names
    )
    return logfile

def sort_out_already_commited_values(self, offered_values_aggregated, offered_flexibility_aggregated, offered_costs_aggregated):

    ''' If there's the same output in the offered power values than those values are not getting attached again'''

    for index, row in offered_values_aggregated.iteritems():

        # Equal values: Actual round's power values are equal to already commited values from previous round(s)
        if offered_values_aggregated.loc[index] == self.commitment_data.loc[index, "Commited power"]:

            offered_values_aggregated.loc[index] = nan
            offered_flexibility_aggregated.loc[index] = nan
            offered_costs_aggregated.loc[index] = nan

        # Greater values: Actual rounds power values are greater than already commited values from previous round(s).
        # Update flex values accordingly, and keep actual rounds power values
        elif offered_values_aggregated.loc[index] > self.commitment_data.loc[index, "Commited power"]:

            offered_flexibility_aggregated.loc[index] = offered_flexibility_aggregated.loc[index] - self.commitment_data.loc[index, "Commited flexibility"]

        # Lower values: Actual rounds power values are lower than already commited values from previous round(s).
        # Update flex values accordingly, and keep actual rounds power values
        elif offered_values_aggregated.loc[index] < self.commitment_data.loc[index, "Commited power"]:

            offered_flexibility_aggregated.loc[index] = self.commitment_data.loc[index, "Commited flexibility"] - offered_flexibility_aggregated.loc[index]

    return offered_values_aggregated, offered_flexibility_aggregated, offered_costs_aggregated


#________________________ EMS Data Storage helper functions ________________________#

def select_prognosis_or_planned_prefix(
                                        self,
                                        device_message):

    # Prognosisrequest selection
    if isnull(self.device_messages.loc[self.environment.now, "Prognosis"]) == True:

        self.device_messages.loc[self.environment.now, "Prognosis"] = device_message
        prefix = "Prog "

    # Flexrequest selection
    else:
        self.device_messages.loc[self.environment.now, "Request"] = device_message
        prefix = "Plan "

    return prefix


#-------------------------- Data storage: Values per device  --------------------------#

def store_prices_per_device(self,
                            commitments):

    # Deviation prices are different at every step related to imbalance market prices of MA
    self.ems_data.loc[self.environment.now, "Deviation price up"] = commitments[-1].deviation_cost_curve.gradient_up
    self.ems_data.loc[self.environment.now, "Deviation price down"] = commitments[-1].deviation_cost_curve.gradient_down

    # Contract Prices:
    # NOTE: self.ems_prices could be adapted (e.g. indexed Series-valeus) for dynamic price schemes (e.g. Day/Nite-tariff)
    self.ems_data.loc[self.environment.now, "Feedin price"] = commitments[0].deviation_cost_curve.gradient_down
    self.ems_data.loc[self.environment.now, "Purchase price"] = commitments[0].deviation_cost_curve.gradient_up

    return

def store_contract_costs_per_device(self,
                                    prefix: str,
                                    index: datetime,
                                    enum: int,
                                    targeted_power_per_device: Series,
                                    device: str) -> Series:

    # If targeted power is positive multiply with purchase price
    if targeted_power_per_device[enum][index] >= 0:
        self.device_data.loc[
                            (index, device),
                            str(prefix + "contract costs")
                                ] = targeted_power_per_device[enum][index] * self.ems_data.loc[self.environment.now, "Purchase price"]

    # If targeted power is negative multiply with feed-in-price
    else:
        self.device_data.loc[
                            (index, device),
                            str(prefix + "contract costs")
                                ] = targeted_power_per_device[enum][index] * self.ems_data.loc[self.environment.now, "Feedin price"]

    return self.device_data.loc[(index, device), str(prefix + "contract costs")]


def store_flexibility_per_device(self,
                                 index: datetime,
                                 prefix: str,
                                 enum: int,
                                 device: str,
                                 targeted_power_per_device,
                                 commitments) -> Series:

    flexibility_per_device = nan
    if "Prog" in prefix:

       # If a prognosis optimization leads to the same values as the old prog power(=planned values from last step), keep planned flex
        if self.device_data.loc[(index, device), "Prog power"] == targeted_power_per_device[enum].loc[index]:
            flexibility_per_device = self.device_data.loc[(index, device), str(prefix + "flexibility")]

        # Update if the prognosis optimization changes the prognosed flex values (=planned flex from the previous step)
        else:
            if self.device_data.loc[(index, device), "Prog power"] > targeted_power_per_device[enum].loc[index]:

                flexibility_per_device = self.device_data.loc[(index, device), "Prog power"] \
                                            - targeted_power_per_device[enum].loc[index]

                self.device_data.loc[(index, device), str(prefix + "flexibility")] = flexibility_per_device

            elif self.device_data.loc[(index, device), "Prog power"] < targeted_power_per_device[enum].loc[index]:

                flexibility_per_device = targeted_power_per_device[enum].loc[index] \
                                            - self.device_data.loc[(index, device), "Prog power"]

                self.device_data.loc[(index, device), str(prefix + "flexibility")] = flexibility_per_device

            else:
                flexibility_per_device = nan

    if "Plan" in prefix:

        if self.device_data.loc[(index, device), "Prog power"] == targeted_power_per_device[enum].loc[index]:
            flexibility_per_device = self.device_data.loc[(index, device), str(prefix + "flexibility")]

        else:
            if self.device_data.loc[(index, device), "Prog power"] > self.device_data.loc[(index, device), "Plan power"]:

                flexibility_per_device = (self.device_data.loc[(index, device), "Prog power"] \
                                            - self.device_data.loc[(index, device), "Plan power"])

                self.device_data.loc[(index, device), str(prefix + "flexibility")] = flexibility_per_device

            elif self.device_data.loc[(index, device), "Prog power"] < self.device_data.loc[(index, device), "Plan power"]:

                flexibility_per_device = (self.device_data.loc[(index, device), "Plan power"] \
                                            - self.device_data.loc[(index, device), "Prog power"])

                self.device_data.loc[(index, device), str(prefix + "flexibility")] = flexibility_per_device



    return flexibility_per_device

#-------------------------- Data storage: Sum over devices per datetime  --------------------------#

def store_requested_power_per_datetime(self,
                                       index: datetime,
                                       prefix: str,
                                       commitments) -> Series:


    requested_power  = commitments[-1].constants.loc[index]

    # Only store non-nan values
    if not isnull(requested_power):

        self.ems_data.loc[index, "Req power"] = requested_power

    return requested_power


def store_requested_flex_per_datetime(self,
                                     index: datetime,
                                     prefix: str,
                                     device_message) -> Series:


    requested_flexibility = device_message.targeted_flexibility.loc[index]

    # Only store non-nan values
    if not isnull(requested_flexibility):

        # All nans gets overwritten with zero at first datetime
        if isnull(self.ems_data.loc[index, "Req flexibility"]):

            self.ems_data.loc[index, "Req flexibility"] = requested_flexibility

        # Only write once again after first datetime
        elif self.ems_data.loc[index, "Req flexibility"] == 0:

            self.ems_data.loc[index, "Req flexibility"] = requested_flexibility

    return self.ems_data.loc[index, str(prefix + "power")]


def store_power_per_datetime(self,
                             index: datetime,
                             prefix: str) -> Series:


    self.ems_data.loc[index, str(prefix + "power")] = self.device_data.loc[
                                                                        IndexSlice[index,:],
                                                                        str(prefix + "power")
                                                                            ].sum(axis="index")

    return self.ems_data.loc[index, str(prefix + "power")]


def store_flexibility_per_datetime(self,
                                   index: datetime,
                                   prefix: str) -> Series:

    if "Plan" in prefix:

        # min_counts helps here to avoid errors due to nan values
        self.ems_data.loc[index, str(prefix + "flexibility")] = self.device_data.loc[
                                                                                IndexSlice[index,:],
                                                                                str(prefix + "flexibility")
                                                                                        ].sum(axis="index", min_count=1)

    return self.ems_data.loc[index, str(prefix + "flexibility")]


def store_contract_costs_per_datetime(self,
                                      index: datetime,
                                      prefix: str,
                                      power_over_all_devices: Series) -> Series:

    if power_over_all_devices >= 0:

        # If power is positive multiply with purchase price
        self.ems_data.loc[index, str(prefix + "contract costs")] = power_over_all_devices \
                                                                    * self.ems_data.loc[self.environment.now, "Purchase price"]
    else:
        # If power is negative multiply with feed in price
        self.ems_data.loc[index, str(prefix + "contract costs")] = power_over_all_devices \
                                                                    * self.ems_data.loc[self.environment.now, "Feedin price"]

    return self.ems_data.loc[index, str(prefix + "contract costs")]


def store_deviation_costs_per_datetime(self,
                                       index: datetime,
                                       prefix: str,
                                       power_over_all_devices: Series,
                                       requested_power: Series) -> Series:

    if power_over_all_devices > requested_power:

        self.ems_data.loc[index, str(prefix + "dev costs")] = (power_over_all_devices - requested_power) \
                                                                        * self.ems_data.loc[self.environment.now, "Deviation price up"]

    elif power_over_all_devices < requested_power:

        self.ems_data.loc[index, str(prefix + "dev costs")] = (requested_power - power_over_all_devices) * -1 \
                                                                        * self.ems_data.loc[self.environment.now, "Deviation price down"]

    return self.ems_data.loc[index, str(prefix + "dev costs")]


def store_flex_costs_per_datetime(self,
                                   index: datetime,
                                   prefix: str,
                                   flexibility_over_all_devices: Series,
                                   ) -> Series:

    self.ems_data.loc[index, str(prefix + "flex costs")] = abs(flexibility_over_all_devices) * self.flex_price

    return self.ems_data.loc[index, str(prefix + "flex costs")]


def store_commitment_costs_per_datetime(self,
                                        index: datetime,
                                        prefix: str,
                                        flex_costs_over_all_devices,
                                        deviation_costs_over_all_devices):

    # if "Plan" in prefix:

    self.ems_data.loc[index, str("Plan commitment costs")] = nan_to_num(deviation_costs_over_all_devices) + flex_costs_over_all_devices\

    return self.ems_data.loc[index, str("Plan commitment costs")]


def store_realised_and_commited_values(self,
                                       commitment,
                                       device_message):

    start = device_message.start
    end = device_message.end - device_message.resolution

    self.device_messages.loc[self.environment.now, "Order"] = device_message

    # Negotiation failed
    if device_message.description is "Failed Negotiation":

        print("\n UTILS: Failed Negotiatio\n")

        # Store actual prognosed values as realised ones. No commitments, no commitment data update.
        self.ems_data.loc[start, "Real power"] = self.ems_data.loc[start, "Prog power"]
        self.ems_data.loc[start, "Real flexibility"] = self.ems_data.loc[start, "Prog flexibility"]
        self.ems_data.loc[start, "Real contract costs"] = self.ems_data.loc[start, "Prog contract costs"]
        self.ems_data.loc[start, "Real flex costs"] = self.ems_data.loc[start, "Prog flex costs"]
        self.ems_data.loc[start, "Real commitment costs"] = self.ems_data.loc[start, "Prog commitment costs"]

    # Negotiation succeeded
    elif "Succeeded Negotiation" in device_message.description:

        print("UTILS: Succeeded Negotiation\n")

        # Storing realised values on EMS level
        self.ems_data.loc[start, "Real power"] = self.ems_data.loc[start, "Plan power"]
        self.ems_data.loc[start, "Real flexibility"] = self.ems_data.loc[start, "Plan flexibility"]
        self.ems_data.loc[start, "Real contract costs"] = self.ems_data.loc[start, "Plan contract costs"]
        self.ems_data.loc[start, "Real flex costs"] = self.ems_data.loc[start, "Plan flex costs"]
        self.ems_data.loc[start, "Real commitment costs"] = self.ems_data.loc[start, "Plan commitment costs"]
        # self.ems_data.loc[start:end, "Prog flexibility"] = self.ems_data.loc[start:end, "Plan flexibility"]

        # Storing commited values and "prognosed next round = planned this round"-operation on EMS-Level
        for index, row in  device_message.targeted_flexibility.iteritems():

            if not isnull(device_message.targeted_flexibility[index]):
                self.ems_data.loc[index, "Com flexibility"] = device_message.targeted_flexibility.loc[index]
                self.ems_data.loc[index, "Prog flexibility"] = device_message.targeted_flexibility.loc[index]
                self.ems_data.loc[index, "Prog dev costs"] = self.ems_data.loc[index, "Plan dev costs"]

            if not isnull(device_message.ordered_power[index]):
                self.ems_data.loc[index, "Com power"] = device_message.ordered_power.loc[index]
                self.ems_data.loc[index, "Prog power"] = device_message.ordered_power[index]

        # Storing realised Device Values
        self.device_data.loc[IndexSlice[start, :], "Real power"] = self.device_data.loc[IndexSlice[start, :], "Plan power"]
        self.device_data.loc[IndexSlice[start, :], "Real flexibility"] = self.device_data.loc[IndexSlice[start, :], "Plan flexibility"]
        self.device_data.loc[IndexSlice[start, :], "Real contract costs"] = self.device_data.loc[IndexSlice[start, :], "Plan contract costs"]

        # "prognosed next round = planned this round"-operation on Device-Level
        self.device_data.loc[IndexSlice[start:end, :], "Prog power"] = self.device_data.loc[IndexSlice[start:end, :], "Plan power"]
        self.device_data.loc[IndexSlice[start:end, :], "Prog flexibility"] = self.device_data.loc[IndexSlice[start:end, :], "Plan flexibility"]
        self.device_data.loc[IndexSlice[start:end, :], "Prog contract costs"] = self.device_data.loc[IndexSlice[start:end, :], "Plan contract costs"]


    # print("EMS: Device message targeted power: {}".format(device_message.ordered_power))
    # print("\nEMS: Device message target flex: {}".format(device_message.targeted_flexibility.loc[start:end]))
    # print("\nEMS: Store commitment constants: {}".format(commitment.constants))
    # print("\nEMS: Store commitment costs: {}".format(commitment.costs))

    # print(self.device_data.loc[:, str("Prog " + "contract costs")])
    # print("\nDEVICE: Prog Contract costs after commitment: {}\n".format(self.device_data.loc[:, str("Prog " + "contract costs")]))
    # print("\nEMS: New EMS Prognosis flexibility: {}".format(self.ems_data.loc[start:end, "Prog flexibility"]))
    # print("\nEMS: Plan deviation costs: {}".format(self.ems_data.loc[start:end, "Plan dev costs"]))
    #
    #
    # print("\nEMS: Commited power values: {}".format(self.ems_data.loc[start:end, "Com power"]))
    # print("\nEMS: Commited flex values: {}".format(self.ems_data.loc[start:end, "Com flexibility"]))
    # print("\nEMS: Realised power values: {}".format(self.ems_data.loc[start:end, "Real power"]))
    # print("\nEMS: Realised flex values: {}".format(self.ems_data.loc[start:end, "Real flexibility"]))
    # print("\nEMS: Realised com costs: {}".format(self.ems_data.loc[start:end, "Real commitment costs"]))
    # print("\nEMS: Planned com costs: {}".format(self.ems_data.loc[start:end, "Plan commitment costs"]))

    return
