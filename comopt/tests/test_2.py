from datetime import datetime, timedelta
from math import sqrt, sin
from pandas import (
    DataFrame,
    MultiIndex,
    IndexSlice,
    set_option,
    plotting,
    concat,
    date_range,
    option_context,
    to_numeric,
)

from comopt.model.environment import Environment
from comopt.scenario.balancing_opportunities import (
    single_curtailment_each_day_between_2_and_3_am,
    single_curtailment_or_shift_each_day_between_10_and_12_am,
    single_curtailment_or_shift_each_day_between_12_and_14_pm,
    generated_imbalance_profile,
)

from comopt.scenario.battery_constraints import limited_battery_capacity_profile

from comopt.scenario.ems_constraints import (
    limited_capacity_profile as grid_connection,
    follow_generated_consumption_profile,
    follow_generated_production_profile,
    follow_solar_profile,
    curtailable_solar_profile,
    curtailable_integer_solar_profile,
    follow_integer_test_profile,
    dispatchable_load_profile_with_bounds
    # curtailable_integer_test_profile,
)

# POLICY FUNCTIONS:
from comopt.scenario.ma_policies import (
    never_buy,
    buy_at_any_cost,
    buy_with_deterministic_prices,
    buy_with_stochastic_prices,
)
from comopt.scenario.ta_policies import (
    never_sell,
    sell_at_any_cost,
    sell_with_deterministic_prices,
    sell_with_stochastic_prices,
    Q_learning,
)

# TA Q-LEARNING EXPLORATION FUNCTIONS:
from comopt.scenario.ta_policies import (
    choose_action_randomly_using_uniform,
    choose_action_greedily_with_noise,
)

# TA Q-LEARNING ACTION FUNCTIONS:
from comopt.scenario.ta_policies import multiply_markup_evenly

# Concession and Noise Curves:
from comopt.model.utils import (
    initialize_series,
    initialize_index,
    linear,
    root_divided_by_2,
    cos_root_divided_by_2,
    no_shape,
    uniform_1,
    gauss_1,
    gauss_2,
    no_noise,
)

from comopt.utils import data_import
from comopt.plotting.negotiation_plots import plot_negotiation_data
from comopt.plotting.profile_plots import plot_ems_data

import time
from random import uniform, randint, gauss, seed

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D

import pickle
import enlopy
import numpy as np
from pandas import Series
from copy import deepcopy


# Set horizon
start_time = time.time()
start = datetime(year=2018, month=6, day=1, hour=12)
end = datetime(year=2018, month=6, day=1, hour=15)
resolution = timedelta(minutes=15)

# Set EMS agents
number_of_agents = 1
ems_names = []
for number in range(1, number_of_agents + 1):
    ems_name = "EMS " + str(number)
    ems_names.append(ems_name)

# --------------OPTIONAL---------------#
# Pickle profile data
pickle_off = open("imbalances_test_profile_1_day.pickle", "rb")
imbalances_test_profile_1_day = pickle.load(pickle_off)
imbalances_test_profile_1_day *= 2
imbalances_test_profile_1_day = abs(imbalances_test_profile_1_day)

i = deepcopy(imbalances_test_profile_1_day[start:end])
i[start:end] = 2
i[3] *= -1
i[7] *= -1
imbalances_test_profile_1_day = deepcopy(i)

pickle_off = open("imbalance_prices_test_profile_1_day.pickle", "rb")
imbalance_prices_test_profile_1_day = pickle.load(pickle_off)
# imbalance_prices_test_profile_1_day *= 10

pickle_off = open("solar_test_profile_1_day.pickle", "rb")
solar_test_profile_1_day = pickle.load(pickle_off)
solar_test_profile_1_day.loc[:] = 10

pickle_off = open("load_test_profile_1_day.pickle", "rb")
load_test_profile_1_day = pickle.load(pickle_off)
load_test_profile_1_day.loc[:] = 6

# Prepare additional profile data
dispatch_factor_load = 0.25
dispatch_factor_solar = 1
# Prices & Costs
purchase_price = 8
feed_in_price = 6
dev_base_price = (purchase_price + feed_in_price) / 2
imbalance_market_costs = (
    abs(imbalances_test_profile_1_day) * imbalance_prices_test_profile_1_day
)
imbalance_market_costs_normalized = imbalance_market_costs / max(imbalance_market_costs)
# imbalance_market_costs_normalized[:] = 10
# deviation_prices = imbalance_market_costs_normalized
deviation_multiplicator = 1

deviation_prices = [
    2 ** x for x in range(4, 4 + len(imbalances_test_profile_1_day.index))
]
deviation_prices = Series(
    index=imbalances_test_profile_1_day.index, data=deviation_prices
)
# deviation_prices = imbalance_market_costs_normalized
# deviation_prices[deviation_prices>0.20] = 1000
# deviation_prices.plot()
# for x in deviation_prices.index:
#     if deviation_prices[x] > 0.2:
#         deviation_prices[x] = deviation_prices[x] + (uniform(0,100))

deviation_prices.plot()
deviation_prices
undispatched_load = load_test_profile_1_day
dispatched_load = enlopy.generate.gen_demand_response(
    load_test_profile_1_day,
    percent_peak_hrs_month=0.33,
    percent_shifted=0.25,
    shave=False,
)
flexible_load_profile = DataFrame(
    index=load_test_profile_1_day.index, columns=["derivative min", "derivative max"]
)

for idx in flexible_load_profile.index:
    flexible_load_profile.loc[idx, "derivative min"] = min(
        dispatched_load[idx], undispatched_load[idx]
    )
    flexible_load_profile.loc[idx, "derivative max"] = max(
        dispatched_load[idx], undispatched_load[idx]
    )

net_demand_without_flex = (
    flexible_load_profile.loc[:, "derivative min"] - solar_test_profile_1_day
)
net_demand_costs = deepcopy(net_demand_without_flex)
net_demand_costs[net_demand_costs > 0] = (
    net_demand_costs[net_demand_costs > 0] * purchase_price
)
net_demand_costs[net_demand_costs < 0] = (
    net_demand_costs[net_demand_costs < 0] * feed_in_price
)
# type(env.ems_agents[0].flex_per_device["Load"][0])
#
# if "nan" in env.ems_agents[0].flex_per_device["Load"][0]:
#     print("Yes")

# ------------OPTIONAL END-------------#

input_data = {
    # Optimiziation Input Parameter:
    "Seed": seed(111),
    # TODO: Find all Flow multipliers and replace it with the input data
    "Flow unit multiplier": resolution.seconds / 3600,
    "Balancing opportunities":
    # single_curtailment_or_shift_each_day_between_10_and_12_am(start=start, end=end, resolution=resolution),
    # single_curtailment_or_shift_each_day_between_12_and_14_pm(start=start, end=end, resolution=resolution),
    generated_imbalance_profile(
        start=start,
        end=end,
        resolution=resolution,
        imbalance_range=(0, 5),
        imbalance_price_1=10,
        imbalance_price_2=8,
        frequency=1,
        window_size=(1, 10),
        imbalance_profile=imbalances_test_profile_1_day,
        imbalance_prices=imbalance_prices_test_profile_1_day,
    ),
    "EMS constraints": [
        grid_connection(start=start, end=end, resolution=resolution, capacity=100)
    ],
    "Device constraints": [
        # Profilenames need to contain "consumption", "generation", "battery", "buffer" as keywords for the plotting function!
        [  # >>>>>> EMS 1 <<<<<#
            # 1) Load
            # follow_generated_consumption_profile(start=start, end=end, resolution=resolution,
            # max_capacity=10, dispatch_factor=dispatch_factor_load, profile=load_test_profile_1_day),
            dispatchable_load_profile_with_bounds(
                start=start,
                end=end,
                resolution=resolution,
                profile=flexible_load_profile,
            ),
            # 2) Generation
            follow_generated_production_profile(
                start=start,
                end=end,
                resolution=resolution,
                max_capacity=10,
                dispatch_factor=dispatch_factor_solar,
                profile=solar_test_profile_1_day,
            ),
            # curtailable_integer_solar_profile(start=start, end=end, resolution=resolution)
            # 3) Battery
            # 4) Buffer
        ],
        [],  # >>>>>> EMS 2 <<<<<#
        [],  # >>>>>> EMS 3 <<<<<#
    ],
    # Left = Shortage, Right = Surplus
    "EMS prices": [(feed_in_price, purchase_price)],
    "MA Deviation Prices": deviation_prices,
    "MA Deviation Multiplicator": deviation_multiplicator,  # can be used to increase the deviation prices in each step
    "MA imbalance_market_costs": imbalance_market_costs,
    "Central optimization": False,
    "MA horizon": timedelta(hours=0.5),
    "TA horizon": timedelta(hours=1),
    "Step_now": 0,
    # Prognosis negotiaton parameter
    "Prognosis rounds": 10,
    "MA prognosis policy": buy_with_stochastic_prices,
    # MA POLICIES:
    # never_buy
    # buy_at_any_cost
    # buy_with_deterministic_prices
    # buy_with_stochastic_prices
    "MA prognosis parameter": {
        "Reservation price": 3,
        "Markup": 1,
        "Concession": root_divided_by_2,  #  linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "Noise": gauss_1,  # uniform_1, gauss_1, gauss_2, no_noise
    },
    "TA prognosis policy": sell_with_stochastic_prices,
    # TA POLICIES:
    # never_sell,
    # sell_at_any_cost,
    # sell_with_deterministic_prices,
    # sell_with_stochastic_prices,
    # Q_learning
    "TA prognosis parameter": {
        "Reservation price": 2,
        "Markup": 1,
        "Concession": linear,  #  linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "Noise": gauss_1,  # uniform_1, gauss_1, gauss_2, no_noise
    },
    "Q parameter prognosis": {
        "Gamma": 0.1,  # Reward discount factor
        "Alpha": 0.1,  # Learning rate
        "Epsilon": 0.2,  # Exploration range: 0 = Always random exploration, 1 = Always Argmax(Q-Value)
        "Action function": multiply_markup_evenly,
        # TA EXP FUNCS:# multiply_markup_evenly
        "Exploration function": choose_action_randomly_using_uniform,
        # TA ACT FUNCS: # choose_action_greedily_with_noise
        # choose_action_randomly_using_uniform
        "Step now": 0,
    },
    # Flexrequest negotiaton parameter
    "Flexrequest rounds": 10,
    "MA flexrequest policy": buy_with_stochastic_prices,
    # MA POLICIES:
    # never_buy
    # buy_at_any_cost
    # buy_with_deterministic_prices
    # buy_with_stochastic_prices
    "MA flexrequest parameter": {
        "Reservation price": 3,  # Placeholder variable
        "Reservation price factor": 2,
        "Markup": 1,  # Placeholder variable
        "Markup factor": 1,
        "Concession": linear,  # linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "Noise": gauss_1,  #  uniform_1, gauss_1, gauss_2, no_noise
        "Sticking factor": 0,  # Close to 0 means little sticking request, close to 1 means a lot of sticking requests
    },
    "TA flexrequest policy": sell_with_stochastic_prices,
    # TA POLICIES:
    # never_sell,
    # sell_at_any_cost,
    # sell_with_deterministic_prices,
    # sell_with_stochastic_prices,
    # Q_learning
    "TA flexrequest parameter": {
        "Reservation price": 2,  # Placeholder variable
        "Markup factor": 1,
        "Markup": 1,  # Placeholder variable
        "Concession": linear,  # linear, root_divided_by_2, cos_root_divided_by_2, no_shape
        "Noise": no_noise,  # #  uniform_1, gauss_1, gauss_2, no_noise
    },
    "Q parameter flexrequest": {
        "Gamma": 0.1,  # Reward discount factor
        "Alpha": 0.1,  # Learning rate
        "Epsilon": 0.2,  # Exploration range: 0 = Always random exploration, 1 = Always Argmax(Q-Value)
        "Action function": multiply_markup_evenly,
        # TA EXP FUNCS:# multiply_markup_evenly
        "Exploration function": choose_action_randomly_using_uniform,
        # TA ACT FUNCS: # choose_action_greedily_with_noise
        # choose_action_randomly_using_uniform
        "Step now": 0,
    },
}

# Set up simulation environment
env = Environment(
    name="Baseline scenario without any FlexRequests.",
    start=start,
    end=end,
    resolution=resolution,
    ems_names=ems_names,
    input_data=input_data,
)

# pickling_on = open("env_1.pickle","wb")
# pickle.dump(env, pickling_on)
# pickling_on.close()

# Run simulation model
env.run_model()
env.plan_board.message_logs
# execution time i minutes
execution_time = (time.time() - start_time) / 60
execution_time
# Cut off head and tail for analysis
cut_head = timedelta(days=1)
cut_tail = timedelta(days=1)
analysis_window = (env.start + cut_head, env.end - env.resolution - cut_tail)

# Analyse simulation results
set_option("display.max_columns", None)
set_option("display.max_colwidth", 20)
set_option("display.width", 200)

# %%
# ems.commitment_prognosis_costs
# ems.commitment_planning_costs
ems = env.ems_agents[0]
# ems.prognosed_power_per_device.concat(ems.planned_power_per_device)
# plt.plot(ems.prognosed_power_per_device["Load"])
# plt.plot(ems.planned_power_per_device["Load"])
#
# ems.realised_power_per_device["Generation"] - ems.planned_power_per_device["Generation"]
# ems.planned_power_per_device["Load"] - ems.realised_power_per_device["Load"]
# ems.prognosed_power_per_device["Generation"] + ems.planned_power_per_device["Generation"]
#
# plt.plot(ems.prognosed_power_per_device["Generation"])
# plt.plot(ems.planned_power_per_device["Generation"])
ems.commitment_planning_costs
env.market_agent.commitments
env.trading_agent.cleared_flex_negotiations
#
# ems.realised_power_per_device
# ems.flex_per_device
# total_flex = ems.flex_per_device["Load"] + abs(ems.flex_per_device["Generation"])
#
# ems.flex_per_device["Load"].values
#
# env.market_agent.balancing_opportunities["Imbalance (in MW)"].apply(to_numeric, errors='ignore')
# env.market_agent.commitments["bought_flex"]
# env.market_agent.deviation_prices
# %%
def plot_ems_data(environment):
    ems = env.ems_agents[0]
    # Plot config
    fontsize_titles = 20
    plt.rcParams["figure.figsize"] = [20, 50]
    plt.rcParams["axes.xmargin"] = 0

    # Create subplots
    gs = gridspec.GridSpec(7, 1, height_ratios=[1, 1, 2, 2, 3, 2, 2])
    gs.update(wspace=0.15, hspace=0.2, bottom=0.5)

    cut_off_indices = int(env.max_horizon / resolution - 1)
    index = env.simulation_runtime_index[:-cut_off_indices]

    # Load profile data MA
    ma_imbalances = env.market_agent.balancing_opportunities["Imbalance (in MW)"].apply(
        to_numeric, errors="ignore"
    )
    ma_imbalance_market_prices = env.market_agent.balancing_opportunities[
        "Price (in EUR/MWh)"
    ].apply(to_numeric, errors="ignore")
    ma_imbalance_market_costs = env.market_agent.imbalance_market_costs.apply(
        to_numeric, errors="ignore"
    )
    ma_bought_flexibility = env.market_agent.commitments["bought_flex"].apply(
        to_numeric, errors="ignore"
    )
    ma_deviation_prices = Series(
        data=env.market_agent.deviation_prices_realised, index=index
    )
    ma_bought_flexibility

    cleared_flex_negotiations = env.trading_agent.cleared_flex_negotiations["Cleared"]

    # Load profile data EMS
    load_without_flex = ems.device_constraints[0].apply(to_numeric, errors="ignore")
    generation_without_flex = ems.device_constraints[1].apply(
        to_numeric, errors="ignore"
    )
    realised_loads = ems.realised_power_per_device["Load"].apply(
        to_numeric, errors="ignore"
    )
    realised_generation = ems.realised_power_per_device["Generation"].apply(
        to_numeric, errors="ignore"
    )

    # Cut simulation horizon from data
    load_without_flex = load_without_flex[:-cut_off_indices]
    generation_without_flex = generation_without_flex[:-cut_off_indices]
    realised_loads = realised_loads[:-cut_off_indices]
    realised_generation = realised_generation[:-cut_off_indices]
    ma_imbalances = ma_imbalances[:-cut_off_indices]
    ma_imbalance_market_prices = ma_imbalance_market_prices[:-cut_off_indices]
    ma_imbalance_market_cost_normalized = (
        ma_imbalance_market_costs / ma_imbalance_market_costs.max()
    )
    ma_imbalance_market_cost_normalized = ma_imbalance_market_cost_normalized[
        start : end - env.max_horizon
    ]
    ma_imbalance_market_costs = ma_imbalance_market_costs[start : end - env.max_horizon]
    ma_bought_flex = ma_bought_flexibility[:-cut_off_indices]
    ma_deviation_prices = ma_deviation_prices[start : end - env.max_horizon]

    # Subplots MA
    ma_imbalance_market_prices_plot = plt.subplot(gs[0, :])
    ma_imbalance_market_costs_plot = plt.subplot(gs[1, :])
    ma_imbalances_plot = plt.subplot(gs[2, :])
    ma_deviation_prices_plot = plt.subplot(gs[3, :])
    net_demand_plot = plt.subplot(gs[4, :])
    load_flex_activated_plot = plt.subplot(gs[5, :])
    generation_flex_activated_plot = plt.subplot(gs[6, :])

    # --------------------- CONFIG -------------------------#

    load_flex_activated_plot.set_ylabel("Power in kW", fontsize=15)
    load_flex_activated_plot.set_xlabel(
        "Net Demand with and without Flex activation", fontsize=15
    )

    generation_flex_activated_plot.set_ylabel("Power in kW", fontsize=15)
    generation_flex_activated_plot.set_xlabel(
        "Net Demand with and without Flex activation", fontsize=15
    )

    # EMS CONFIG: Net demand without flex
    net_demand_plot.set_ylabel("Power in kW", fontsize=15)
    net_demand_plot.set_xlabel(
        "Net Demand with and without Flex activation", fontsize=15
    )

    # --------------------- MA PLOTS -------------------------#
    ma_imbalance_market_prices_plot.plot(
        index, ma_imbalance_market_prices, color="red", linewidth=3
    )
    ma_imbalances_plot.bar(
        x=index,
        height=ma_bought_flex,
        width=0.01,
        color="white",
        alpha=1,
        edgecolor="red",
        linewidth=5,
        linestyle="solid",
    )
    ma_imbalances_plot.bar(
        x=index,
        height=ma_imbalances,
        width=0.01,
        facecolor="grey",
        alpha=0.3,
        edgecolor="black",
        linewidth=3,
        linestyle="solid",
    )
    ma_imbalances_plot.plot(
        cleared_flex_negotiations, linewidth=0, linestyle="solid", marker="o"
    )

    ma_imbalance_market_costs_plot.plot(
        index, ma_imbalance_market_cost_normalized, color="green", linewidth=3
    )
    ma_imbalance_market_costs_plot.fill_between(
        index, 0, ma_imbalance_market_cost_normalized, color="green", alpha=0.15
    )
    ma_deviation_prices_plot.bar(
        x=index,
        height=ma_deviation_prices,
        width=0.01,
        color="lightblue",
        alpha=0.8,
        edgecolor="black",
        linewidth=2,
        linestyle="solid",
    )
    ma_deviation_prices_plot.bar(
        x=index,
        height=-ma_deviation_prices,
        width=0.01,
        color="blue",
        alpha=0.35,
        edgecolor="black",
        linewidth=2,
        linestyle="solid",
    )
    # --------------------- EMS PLOTS -------------------------#
    # EMS PLOT: load profile (check if is curtailable)
    if load_without_flex["derivative equals"].isnull().all():
        flexible_load_lower_bound = load_without_flex["derivative min"]
        flexible_load_upper_bound = load_without_flex["derivative max"]
        net_demand_plot.plot(
            index, flexible_load_lower_bound, color="blue", linestyle="dashed"
        )
        net_demand_plot.plot(
            index, flexible_load_upper_bound, color="blue", linestyle="dashed"
        )
        net_demand_plot.fill_between(
            index,
            flexible_load_lower_bound,
            flexible_load_upper_bound,
            color="lightblue",
            alpha=0.5,
        )
        load_flex_activated_plot.plot(
            index, flexible_load_lower_bound, color="blue", linestyle="dashed"
        )
        load_flex_activated_plot.plot(
            index, flexible_load_upper_bound, color="blue", linestyle="dashed"
        )
        load_flex_activated_plot.fill_between(
            index,
            flexible_load_lower_bound,
            flexible_load_upper_bound,
            color="lightblue",
            alpha=0.5,
        )
        load_flex_activated_plot.fill_between(
            index, flexible_load_lower_bound, realised_loads, color="red", alpha=0.5
        )
        load_flex_activated_plot.plot(
            index,
            realised_loads,
            color="black",
            linestyle="solid",
            linewidth=3,
            label="Realised Power",
        )
        load_without_flex = flexible_load_lower_bound

    # # EMS PLOT: generation profile (check if is curtailable)
    if generation_without_flex["derivative equals"].isnull().all():
        full_curtailable_generation = generation_without_flex["derivative min"]
        net_demand_plot.plot(index, full_curtailable_generation, linestyle="dashed")
        net_demand_plot.fill_between(
            index, 0, full_curtailable_generation, color="orange", alpha=0.5
        )
        generation_flex_activated_plot.plot(
            index,
            realised_generation,
            color="black",
            linestyle="solid",
            linewidth=3,
            label="Realised Power",
        )
        generation_flex_activated_plot.plot(
            index, full_curtailable_generation, linestyle="dashed"
        )
        generation_flex_activated_plot.fill_between(
            index, 0, full_curtailable_generation, color="orange", alpha=0.5
        )
        generation_flex_activated_plot.fill_between(
            index,
            realised_generation,
            full_curtailable_generation,
            color="red",
            alpha=0.5,
        )
        generation_without_flex = full_curtailable_generation

    # EMS PLOT: net demand without flex
    net_demand_without_flex = load_without_flex + generation_without_flex
    net_demand_plot.plot(
        index,
        net_demand_without_flex,
        color="black",
        linewidth=3,
        linestyle="dashed",
        label="Net Demand",
    )

    # EMS PLOT: net demand with flex
    net_demand_with_flex = realised_loads + realised_generation
    net_demand_plot.plot(
        index,
        net_demand_with_flex,
        color="black",
        linewidth=3,
        label="Net Demand + Flex",
    )
    net_demand_plot.fill_between(
        index,
        net_demand_without_flex,
        net_demand_with_flex,
        color="red",
        alpha=0.5,
        label="Flexibilty",
    )
    net_demand_plot.legend(
        loc="upper left", fancybox=True, ncol=6, fontsize=14, framealpha=0.8
    )

    for ax in [
        net_demand_plot,
        generation_flex_activated_plot,
        load_flex_activated_plot,
        ma_imbalance_market_prices_plot,
        ma_imbalances_plot,
        ma_imbalance_market_costs_plot,
        ma_deviation_prices_plot,
    ]:
        ax.set_ylabel("Power in kW", fontsize=15)
        # ax.load_flex_activated_plot.set_xlabel('Simulation Runtime', fontsize=15)
        # ax.title.set_xlabel('Profile with and without Flex activation', fontsize=15)
        ax.xaxis.grid(True)
        # ax.set_xticks(index)
        plt.xticks(fontsize=14, rotation=-90)
        plt.yticks(fontsize=14, rotation=0)
        ax.axhline(y=0, color="grey")

    # for ax in []:
    #     ax.set_ylabel('Power in kW', fontsize=15)
    #     ax.load_flex_activated_plot.set_xlaYbel('Simulation Runtime', fontsize=15)
    #     ax.xaxis.grid(True)
    #     # ax.set_xticks(index)
    #     plt.xticks(fontsize=14, rotation=-90)
    #     plt.yticks(fontsize=14, rotation=0)
    #     ax.axhline(y=0,color='grey')
    return plt


plot_ems_data(env)
env.market_agent.commitments["bought_flex"]

# %%
plt_1 = plot_negotiation_data(
    negotiation_data_df=env.plan_board.prognosis_negotiation_log_1,
    q_tables=env.trading_agent.stored_q_tables_prognosis_1,
    action_tables=env.trading_agent.stored_action_tables_prognosis_1,
    input_data=input_data,
)
plt_2 = plot_negotiation_data(
    negotiation_data_df=env.plan_board.flexrequest_negotiation_log_1,
    q_tables=env.trading_agent.stored_q_tables_flexrequest_1,
    action_tables=env.trading_agent.stored_action_tables_flexrequest_1,
    input_data=input_data,
)
