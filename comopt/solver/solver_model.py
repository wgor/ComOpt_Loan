from pyomo.environ import *
from pyomo.core.base.block import *
from pyomo.opt import SolverFactory
from pyomo.core import (
    Var,
    Set,
    Param,
    NonNegativeReals,
    Binary,
    Constraint,
    Objective,
    minimize,
    ConcreteModel,
)
from datetime import datetime, timedelta
import pandas as pd

from comopt.solver.utils import preprocess_solver_data


def create_solver_model(name: str, data: pd.DataFrame) -> ConcreteModel:
    # TODO: Add efficiency parameter for storages
    # TODO: Write Docstring
    # TODO: Attach buffer data to data or create on input file for buffer_windows_list and buffer_windows_timeperiods

    # Extract some data from data input
    idx = pd.IndexSlice
    preprocessed_solver_data = preprocess_solver_data(data)
    activated_device_names = preprocessed_solver_data[0]
    activated_device_types = preprocessed_solver_data[1]
    buffer_windows_list = preprocessed_solver_data[2]
    buffer_windows_timeperiods = preprocessed_solver_data[3]

    # Create model
    model = ConcreteModel(name=name)

    # ------------------------  Parameter & Set Rules  ----------------------------- #
    def integral_equal_select(model, timeperiod, ems, device=None):
        # this works because it should be the same value on the ems level
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_integral_equal"])
        else:
            return float(data.loc[(timeperiod, ems, device), "integral_equal"])

    def integral_max_select(model, timeperiod, ems, device=None):
        # this works because it should be the same value on the ems level
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_integral_max"])
        else:
            return float(data.loc[(timeperiod, ems, device), "integral_max"])

    def integral_min_select(model, timeperiod, ems, device=None):
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_integral_min"])
        else:
            return float(data.loc[(timeperiod, ems, device), "integral_min"])

    def derivative_equal_select(model, timeperiod, ems, device=None):
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_derivative_equal"])
        else:
            return float(data.loc[(timeperiod, ems, device), "derivative_equal"])

    def derivative_max_select(model, timeperiod, ems, device=None):
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_derivative_max"])
        else:
            return float(data.loc[(timeperiod, ems, device), "derivative_max"])

    def derivative_min_select(model, timeperiod, ems, device=None):
        if device is None:
            return max(data.loc[(timeperiod, ems), "ems_derivative_min"])
        else:
            return float(data.loc[(timeperiod, ems, device), "derivative_min"])

    def SOC_init_select(model, ems, storage):
        return float(data.loc[(model.timeperiods[1], ems, storage), "integral_equal"])

    def SOC_end_select(model, ems, storage):
        return float(data.loc[(model.timeperiods[-1], ems, storage), "integral_equal"])

    def net_generation_price_select(model, timeperiod, ems):
        return float(data.loc[(timeperiod, ems), "feed_in_tariff"].unique())

    def net_demand_price_select(model, timeperiod, ems):
        return float(data.loc[(timeperiod, ems), "market_price"].unique())

    def buffer_window_timeperiods_select(model, buffer_window, ems):
        return buffer_windows_timeperiods[buffer_window]

    # ------------------------------------ # SETS # --------------------------------------- #
    model.timeperiods = Set(
        initialize=data.index.get_level_values(level="time").unique().values.tolist(),
        ordered=True,
        doc="Set of timeperiods",
    )

    model.ems = Set(
        initialize=data.index.get_level_values(level="ems").unique().values.tolist(),
        ordered=True,
        doc="Set of energy management systems",
    )

    model.nonshiftable_loads = Set(
        initialize=[
            device for device in activated_device_names if "_Load_NON" in device
        ],
        ordered=True,
        doc="Set of nonshiftable load devices",
    )

    model.storages = Set(
        initialize=[
            device for device in activated_device_names if "_Storage" in device
        ],
        ordered=True,
        doc="Set of storage devices",
    )

    model.buffers = Set(
        initialize=[device for device in activated_device_names if "_Buffer" in device],
        ordered=True,
        doc="Set of buffer devices by name",
    )

    model.buffer_windows = Set(
        initialize=buffer_windows_list,
        ordered=True,
        doc="Set of buffer shifting windows by name",
    )

    model.buffer_windows_timeperiods = Set(
        model.buffer_windows,
        model.ems,
        initialize=buffer_window_timeperiods_select,
        ordered=True,
        doc="Sets of timeperiods for each buffer window",
    )

    model.nonshiftable_generators = Set(
        initialize=[
            device for device in activated_device_names if "_Gen_NON" in device
        ],
        ordered=True,
        doc="Set of nonshiftable generator devices",
    )

    model.shiftable_generators = Set(
        initialize=[
            device for device in activated_device_names if "_Gen_SHIFT" in device
        ],
        ordered=True,
        doc="Set of shiftable generator devices",
    )

    # ----------------------------------- # parameter DEVICES level # --------------------------------------- #
    # Nonshiftable Load Devices
    if activated_device_types["Loads_NON"] == "Active":
        model.demand_nonshiftables = Param(
            model.timeperiods,
            model.ems,
            model.nonshiftable_loads,
            initialize=derivative_equal_select,
        )

    # Nonshiftable Generator Devices
    if activated_device_types["Gen_NON"] == "Active":
        model.generation_nonshiftables = Param(
            model.timeperiods,
            model.ems,
            model.nonshiftable_generators,
            initialize=derivative_equal_select,
        )

    # Storage Devices
    if activated_device_types["Storages"] == "Active":
        model.storages_max_power_per_step = Param(
            model.timeperiods,
            model.ems,
            model.storages,
            initialize=derivative_max_select,
        )

        model.storages_min_power_per_step = Param(
            model.timeperiods,
            model.ems,
            model.storages,
            initialize=derivative_min_select,
        )

        model.storages_SOC_init = Param(
            model.ems, model.storages, initialize=SOC_init_select
        )

        model.storages_SOC_end = Param(
            model.ems, model.storages, initialize=SOC_end_select
        )

    # Buffer devices
    if activated_device_types["Buffers"] == "Active":
        model.buffers_max_power_per_window = Param(
            model.timeperiods,
            model.ems,
            model.buffers,
            initialize=derivative_max_select,
        )

        model.buffers_min_power_per_window = Param(
            model.timeperiods,
            model.ems,
            model.buffers,
            initialize=derivative_min_select,
        )

    # Shiftable Generator devices
    if activated_device_types["Gen_SHIFT"] == "Active":
        model.shiftable_generator_max_power_per_step = Param(
            model.timeperiods,
            model.ems,
            model.shiftable_generators,
            initialize=derivative_max_select,
        )

        model.shiftable_generator_min_power_per_step = Param(
            model.timeperiods,
            model.ems,
            model.shiftable_generators,
            initialize=derivative_min_select,
        )

    # ---------------------------------------- # parameter EMS level # --------------------------------------------- #
    model.net_generation_max_per_step = Param(
        model.timeperiods, model.ems, initialize=derivative_max_select
    )

    model.net_demand_max_per_step = Param(
        model.timeperiods, model.ems, initialize=derivative_max_select
    )

    model.net_generation_prices = Param(
        model.timeperiods, model.ems, initialize=net_generation_price_select
    )

    model.net_demand_prices = Param(
        model.timeperiods, model.ems, initialize=net_demand_price_select
    )

    # -------------------------------------- # variables STORAGES level # -------------------------------------------- #
    if activated_device_types["Storages"] == "Active":
        model.storages_charging = Var(
            model.timeperiods, model.ems, model.storages, within=NonNegativeReals
        )

        model.storages_discharging = Var(
            model.timeperiods, model.ems, model.storages, within=NonNegativeReals
        )

        model.storages_SOC = Var(
            model.timeperiods, model.ems, model.storages, within=NonNegativeReals
        )

        model.storages_charging_active = Var(
            model.timeperiods, model.ems, model.storages, within=Binary
        )

        model.storages_discharging_active = Var(
            model.timeperiods, model.ems, model.storages, within=Binary
        )

    # ---------------------------------------- # variables BUFFER level # ----------------------------------------------- #
    if activated_device_types["Buffers"] == "Active":
        model.buffers_charging = Var(
            model.timeperiods, model.ems, model.buffers, within=NonNegativeReals
        )

    # ------------------------------------------ # variables EMS level # ------------------------------------------------- #
    model.net_demand = Var(model.timeperiods, model.ems, within=NonNegativeReals)

    model.net_generation = Var(model.timeperiods, model.ems, within=NonNegativeReals)

    model.net_demand_active = Var(model.timeperiods, model.ems, within=Binary)

    model.net_generation_active = Var(model.timeperiods, model.ems, within=Binary)

    # ------------------------------------------- # rules STORAGES level # ----------------------------------------------- #
    def storages_operation_mode_rule(model, timeperiod, ems, storages):
        return (
            model.storages_charging_active[timeperiod, ems, storages]
            + model.storages_discharging_active[timeperiod, ems, storages]
            <= 1
        )

    def storages_min_charging_rule(model, timeperiod, ems, storages):
        return (
            model.storages_charging_active[timeperiod, ems, storages]
            * model.storages_min_power_per_step[timeperiod, ems, storages]
            <= model.storages_charging[timeperiod, ems, storages]
        )

    def storages_max_charging_rule(model, timeperiod, ems, storages):
        return (
            model.storages_charging_active[timeperiod, ems, storages]
            * model.storages_max_power_per_step[timeperiod, ems, storages]
            >= model.storages_charging[timeperiod, ems, storages]
        )

    def storages_min_discharging_rule(model, timeperiod, ems, storages):
        return (
            model.storages_discharging_active[timeperiod, ems, storages]
            * model.storages_min_power_per_step[timeperiod, ems, storages]
            <= model.storages_discharging[timeperiod, ems, storages]
        )

    def storages_max_discharging_rule(model, timeperiod, ems, storages):
        return (
            model.storages_discharging_active[timeperiod, ems, storages]
            * model.storages_max_power_per_step[timeperiod, ems, storages]
            >= model.storages_discharging[timeperiod, ems, storages]
        )

    def storages_state_of_charge_rule(model, timeperiod, ems, storages):
        if timeperiod == model.timeperiods[1]:
            return (
                model.storages_SOC[timeperiod, ems, storages]
                == model.storages_SOC_init[ems, storages]
                + model.storages_charging[timeperiod, ems, storages]
                - model.storages_discharging[timeperiod, ems, storages]
            )

        elif timeperiod == model.timeperiods[-1]:
            return (
                model.storages_SOC_end[ems, storages]
                == model.storages_SOC[timeperiod - 1, ems, storages]
                + model.storages_charging[timeperiod, ems, storages]
                - model.storages_discharging[timeperiod, ems, storages]
            )
        else:
            return (
                model.storages_SOC[timeperiod, ems, storages]
                == model.storages_SOC[timeperiod - 1, ems, storages]
                + model.storages_charging[timeperiod, ems, storages]
                - model.storages_discharging[timeperiod, ems, storages]
            )

    if activated_device_types["Storages"] == "Active":
        model.battery_operation_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_operation_mode_rule,
        )

        model.battery_min_charging_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_min_charging_rule,
        )

        model.battery_max_charging_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_max_charging_rule,
        )

        model.battery_min_discharging_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_min_discharging_rule,
        )

        model.battery_max_discharging_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_max_discharging_rule,
        )

        model.battery_state_of_charge_constraint = Constraint(
            model.timeperiods,
            model.ems,
            model.storages,
            rule=storages_state_of_charge_rule,
        )

    # -------------------------------------------- # rules BUFFERS level # ----------------------------------------------- #
    def buffers_min_charging_rule(model, timeperiod, ems, buffer):
        return (
            model.buffers_min_power_per_window[timeperiod, ems, buffer]
            <= model.buffers_charging[timeperiod, ems, buffer]
        )

    def buffers_max_charging_rule(model, timeperiod, ems, buffer):
        return (
            model.buffers_max_power_per_window[timeperiod, ems, buffer]
            >= model.buffers_charging[timeperiod, ems, buffer]
        )

    def net_balance_buffers_rule(model, ems, buffer_window):
        return sum(
            model.buffers_charging[timeperiod, ems, buffer]
            for buffer in model.buffers
            for timeperiod in model.buffer_windows_timeperiods[buffer_window, ems]
        ) == max(
            data.loc[idx[timeperiod, ems, buffer], "integral_equal"]
            for buffer in model.buffers
            for timeperiod in model.buffer_windows_timeperiods[buffer_window, ems]
        )

    if activated_device_types["Buffers"] == "Active":
        model.buffer_balancing_constraint = Constraint(
            model.ems, model.buffer_windows, rule=net_balance_buffers_rule
        )

        model.buffer_max_charging_constraint = Constraint(
            model.timeperiods, model.ems, model.buffers, rule=buffers_max_charging_rule
        )

        model.buffer_min_charging_constraint = Constraint(
            model.timeperiods, model.ems, model.buffers, rule=buffers_min_charging_rule
        )

    # ---------------------------------------------- # rules EMS level # -------------------------------------------------- #
    def balancing_ems_net_energy_rule(model, timeperiod, ems):
        return (
            sum(
                model.demand_nonshiftables[timeperiod, ems, load]
                for load in model.nonshiftable_loads
                if activated_device_types["Loads_NON"] == "Active"
            )
            + sum(
                model.storages_charging[timeperiod, ems, storage]
                for storage in model.storages
                if activated_device_types["Storages"] == "Active"
            )
            + sum(
                model.buffers_charging[timeperiod, ems, buffer]
                for buffer in model.buffers
                if activated_device_types["Buffers"] == "Active"
            )
            + model.net_generation[timeperiod, ems]
            == sum(
                model.generation_nonshiftables[timeperiod, ems, generator]
                for generator in model.nonshiftable_generators
                if activated_device_types["Gen_NON"] == "Active"
            )
            + sum(
                model.storages_discharging[timeperiod, ems, storage]
                for storage in model.storages
                if activated_device_types["Storages"] == "Active"
            )
            + model.net_demand[timeperiod, ems]
        )

    def grid_interaction_rule(model, timeperiod, ems):
        return (
            model.net_demand_active[timeperiod, ems]
            + model.net_generation_active[timeperiod, ems]
            <= 1
        )

    def net_demand_max_per_step_rule(model, timeperiod, ems):
        return (
            model.net_demand[timeperiod, ems]
            <= model.net_demand_active[timeperiod, ems]
            * model.net_generation_max_per_step[timeperiod, ems]
        )

    def net_generation_max_per_step_rule(model, timeperiod, ems):
        return (
            model.net_generation[timeperiod, ems]
            <= model.net_generation_active[timeperiod, ems]
            * model.net_generation_max_per_step[timeperiod, ems]
        )

    # ------------------------------------------- # constraints EMS level # ------------------------------------------------- #
    model.balancing_ems_constraint = Constraint(
        model.timeperiods, model.ems, rule=balancing_ems_net_energy_rule
    )

    model.net_demand_maximum_constraint = Constraint(
        model.timeperiods, model.ems, rule=net_demand_max_per_step_rule
    )

    model.net_generation_maximum_constraint = Constraint(
        model.timeperiods, model.ems, rule=net_generation_max_per_step_rule
    )

    # --------------------------------------------- # objective function # ---------------------------------------------------- #
    def objective_function(model):
        return sum(
            model.net_demand[timeperiods, ems]
            * model.net_demand_prices[timeperiods, ems]
            - model.net_generation[timeperiods, ems]
            * model.net_generation_prices[timeperiods, ems]
            for timeperiods in model.timeperiods
            for ems in model.ems
        )

    model.objective_function = Objective(rule=objective_function, sense=minimize)
    # -------------------------------------------- # objective function end # -------------------------------------------------- #
    return model


def solve_schedule(model: ConcreteModel):
    opt = SolverFactory("glpk")
    return opt.solve(model)
