import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pandas import DataFrame, Series, to_numeric
import numpy as np
from numpy import exp, poly1d, polyfit, unique, asarray
from comopt.model.ems import EMS
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
import matplotlib as mpl
import matplotlib.dates as mdates


def plot_ems_net_demand_data(environment):
    # plt.rcParams['axes.xmargin'] = 0
    fontsize_titles = 16
    fontsize_legends = 13
    y_label_size = 14
    start = environment.start
    end = environment.end
    resolution = environment.resolution

    # Create subplots
    plt.figure(figsize=(20, 10))
    plt.rcParams["axes.xmargin"] = 0
    ticklabel_size = 14
    mpl.rcParams["xtick.labelsize"] = ticklabel_size
    mpl.rcParams["ytick.labelsize"] = ticklabel_size

    gs = gridspec.GridSpec(1, 1, height_ratios=[1])
    gs.update(wspace=0.15, hspace=0.5, bottom=0.2)

    cut_off_indices = int(environment.max_horizon / resolution - 1)
    index = environment.simulation_runtime_index[:-cut_off_indices]

    for ems in environment.ems_agents:

        planned_costs = Series(
            index=index,
            data=[
                sum(ems.planned_costs_over_horizons[idx])
                for idx in ems.planned_costs_over_horizons
            ],
        )
        cum_planned_costs = planned_costs.cumsum()
        realised_costs = Series(
            index=index, data=[c.costs for c in ems.commitments[1:]]
        )
        cum_realised_costs = realised_costs.cumsum()

        planned_costs_horizons = DataFrame(index=index, columns=index)
        cnt = 0
        for enum1, idx1 in enumerate(planned_costs_horizons.index):
            for enum2, val in enumerate(ems.planned_costs_over_horizons[idx1]):
                try:
                    planned_costs_horizons.iloc[enum1, enum2 + cnt] = val
                except:
                    pass
            cnt += 1

        realised_costs_horizons = DataFrame(index=index, columns=index)
        cnt = 0
        for enum1, idx1 in enumerate(realised_costs_horizons.index):
            for enum2, val in enumerate(ems.realised_costs_over_horizons[idx1]):
                try:
                    realised_costs_horizons.iloc[enum1, enum2 + cnt] = val
                except:
                    pass
            cnt += 1

        # Load profile data EMS
        load_without_flex = ems.device_constraints[0].apply(to_numeric, errors="ignore")
        generation_without_flex = ems.device_constraints[1].apply(
            to_numeric, errors="ignore"
        )

        for idx in ems.targeted_flex.index:
            ems.targeted_flex.fillna(0, inplace=True)
            ems.targeted_flex[idx] = int(ems.targeted_flex[idx])

        EMS_targeted_flex = ems.targeted_flex.apply(to_numeric, errors="ignore")

        planned_flex_loads = ems.planned_flex_per_device["Load"].apply(
            to_numeric, errors="ignore"
        )
        planned_flex_generation = ems.planned_flex_per_device["Generation"].apply(
            to_numeric, errors="ignore"
        )
        realised_flex_loads = ems.realised_flex_per_device["Load"].apply(
            to_numeric, errors="ignore"
        )
        realised_flex_generation = ems.realised_flex_per_device["Generation"].apply(
            to_numeric, errors="ignore"
        )

        planned_loads = ems.planned_power_per_device["Load"].apply(
            to_numeric, errors="ignore"
        )
        planned_generation = ems.planned_power_per_device["Generation"].apply(
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
        EMS_targeted_flex = EMS_targeted_flex[:-cut_off_indices]
        planned_flex_loads = planned_flex_loads[:-cut_off_indices]
        planned_flex_generation = planned_flex_generation[:-cut_off_indices]
        realised_flex_loads = realised_flex_loads[:-cut_off_indices]
        realised_flex_generation = realised_flex_generation[:-cut_off_indices]
        planned_loads = planned_loads[:-cut_off_indices]
        planned_generation = planned_generation[:-cut_off_indices]
        realised_loads = realised_loads[:-cut_off_indices]
        realised_generation = realised_generation[:-cut_off_indices]

        # --------------------- SUBPLOTS -------------------------#
        net_demand_plot = plt.subplot(gs[0, :])
        # --------------------- CONFIG -------------------------#

        # TITLES
        net_demand_plot.set_title(
            "[Net Demand Profile] X [Net Demand Profile + Realised Flex Activation]",
            fontsize=fontsize_titles,
        )

        # --------------------- EMS PLOTS -------------------------#
        # EMS PLOT: load profile (check if is curtailable)
        if load_without_flex["derivative equals"].isnull().all():

            flexible_load_lower_bound = load_without_flex["derivative min"]
            flexible_load_upper_bound = load_without_flex["derivative max"]

            net_demand_plot.plot(
                index,
                flexible_load_lower_bound,
                color="blue",
                linestyle="",
                label="Min",
            )
            net_demand_plot.plot(
                index,
                realised_loads,
                color="purple",
                linestyle="dashed",
                alpha=1,
                label="Max",
            )
            net_demand_plot.fill_between(
                index,
                flexible_load_lower_bound,
                flexible_load_upper_bound,
                color="lightblue",
                alpha=0.5,
                label="Activateable",
            )

        else:
            # TODO
            pass

        # # EMS PLOT: generation profile (check if is curtailable)
        if generation_without_flex["derivative equals"].isnull().all():

            full_curtailable_generation = generation_without_flex["derivative min"]

            net_demand_plot.plot(
                index,
                full_curtailable_generation,
                linestyle="",
                color="orange",
                label="Max",
            )
            net_demand_plot.plot(
                index,
                realised_generation,
                linestyle="dashed",
                color="orange",
                label="Max",
            )
            net_demand_plot.fill_between(
                index,
                0,
                full_curtailable_generation,
                color="orange",
                alpha=0.5,
                label="Curtailable",
            )

        else:
            # TODO
            pass

        # EMS PLOT: net demand without flex
        net_demand_without_flex = load_without_flex + generation_without_flex
        net_demand_plot.plot(
            index,
            net_demand_without_flex,
            color="black",
            linewidth=3,
            linestyle="dashed",
            label="No Flex",
        )

        # EMS PLOT: net demand with flex
        net_demand_with_flex = realised_loads + realised_generation
        net_demand_plot.plot(
            index,
            net_demand_with_flex,
            color="black",
            linewidth=3,
            label="Flex activated",
        )
        net_demand_plot.fill_between(
            index,
            net_demand_without_flex,
            net_demand_with_flex,
            color="red",
            alpha=0.5,
            label="Flexibilty",
        )

        # NET DEMAND CONFIG
        for ax in [net_demand_plot]:
            ax.set_ylabel("kWh", fontsize=14)
            ax.xaxis.grid(True)
            ax.set_xticks(index)
            ax.set_xticklabels(index, rotation=90)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            # ax.xaxis.set_major_locator(mdates.DayLocator())
            # ax.xaxis.set_minor_formatter(mdates.DateFormatter("%H:%M"))
            ax.axhline(y=0, color="grey")

            # plt.xticks(fontsize=24)
        # Legends
        net_demand_plot.legend(loc="best", ncol=4, fontsize=fontsize_legends)

        plt.savefig("EMS_Data.pdf", transparent=True, quality=100, frameon=False)


def plot_ems_data(environment):
    # plt.rcParams['axes.xmargin'] = 0
    fontsize_titles = 16
    fontsize_legends = 13
    y_label_size = 14
    start = environment.start
    end = environment.end
    resolution = environment.resolution

    # Create subplots
    plt.figure(figsize=(20, 60))
    plt.rcParams["axes.xmargin"] = 0
    ticklabel_size = 14
    mpl.rcParams["xtick.labelsize"] = ticklabel_size
    mpl.rcParams["ytick.labelsize"] = ticklabel_size

    gs = gridspec.GridSpec(9, 1, height_ratios=[2, 1, 1, 1, 1, 1, 1, 2, 2])
    gs.update(wspace=0.15, hspace=0.5, bottom=0.2)

    cut_off_indices = int(environment.max_horizon / resolution - 1)
    index = environment.simulation_runtime_index[:-cut_off_indices]

    for ems in environment.ems_agents:

        planned_costs = Series(
            index=index,
            data=[
                sum(ems.planned_costs_over_horizons[idx])
                for idx in ems.planned_costs_over_horizons
            ],
        )
        cum_planned_costs = planned_costs.cumsum()
        realised_costs = Series(
            index=index, data=[c.costs for c in ems.commitments[1:]]
        )
        cum_realised_costs = realised_costs.cumsum()

        planned_costs_horizons = DataFrame(index=index, columns=index)
        cnt = 0
        for enum1, idx1 in enumerate(planned_costs_horizons.index):
            for enum2, val in enumerate(ems.planned_costs_over_horizons[idx1]):
                try:
                    planned_costs_horizons.iloc[enum1, enum2 + cnt] = val
                except:
                    pass
            cnt += 1

        realised_costs_horizons = DataFrame(index=index, columns=index)
        cnt = 0
        for enum1, idx1 in enumerate(realised_costs_horizons.index):
            for enum2, val in enumerate(ems.realised_costs_over_horizons[idx1]):
                try:
                    realised_costs_horizons.iloc[enum1, enum2 + cnt] = val
                except:
                    pass
            cnt += 1

        # Load profile data EMS
        load_without_flex = ems.device_constraints[0].apply(to_numeric, errors="ignore")
        generation_without_flex = ems.device_constraints[1].apply(
            to_numeric, errors="ignore"
        )

        for idx in ems.targeted_flex.index:
            ems.targeted_flex.fillna(0, inplace=True)
            ems.targeted_flex[idx] = int(ems.targeted_flex[idx])

        EMS_targeted_flex = ems.targeted_flex.apply(to_numeric, errors="ignore")

        planned_flex_loads = ems.planned_flex_per_device["Load"].apply(
            to_numeric, errors="ignore"
        )
        planned_flex_generation = ems.planned_flex_per_device["Generation"].apply(
            to_numeric, errors="ignore"
        )
        realised_flex_loads = ems.realised_flex_per_device["Load"].apply(
            to_numeric, errors="ignore"
        )
        realised_flex_generation = ems.realised_flex_per_device["Generation"].apply(
            to_numeric, errors="ignore"
        )

        planned_loads = ems.planned_power_per_device["Load"].apply(
            to_numeric, errors="ignore"
        )
        planned_generation = ems.planned_power_per_device["Generation"].apply(
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
        EMS_targeted_flex = EMS_targeted_flex[:-cut_off_indices]
        planned_flex_loads = planned_flex_loads[:-cut_off_indices]
        planned_flex_generation = planned_flex_generation[:-cut_off_indices]
        realised_flex_loads = realised_flex_loads[:-cut_off_indices]
        realised_flex_generation = realised_flex_generation[:-cut_off_indices]
        planned_loads = planned_loads[:-cut_off_indices]
        planned_generation = planned_generation[:-cut_off_indices]
        realised_loads = realised_loads[:-cut_off_indices]
        realised_generation = realised_generation[:-cut_off_indices]

        # --------------------- SUBPLOTS -------------------------#
        net_demand_plot = plt.subplot(gs[0, :])
        load_flex_activated_plot = plt.subplot(gs[1, :])
        generation_flex_activated_plot = plt.subplot(gs[2, :])

        realised_flex_plot = plt.subplot(gs[3, :])
        realised_costs_horizons_plot = plt.subplot(gs[4, :])
        planned_flex_plot = plt.subplot(gs[5, :])
        planned_costs_horizons_plot = plt.subplot(gs[6, :])

        commitment_costs_plot = plt.subplot(gs[7, :])
        cumulative_commitment_costs_plot = plt.subplot(gs[8, :])
        # --------------------- CONFIG -------------------------#

        # TITLES
        net_demand_plot.set_title(
            "[Net Demand Profile] X [Net Demand Profile + Realised Flex Activation]",
            fontsize=fontsize_titles,
        )
        load_flex_activated_plot.set_title(
            "[Load Profile] X [Load profile + Planned/Realised Flex Activation]",
            fontsize=fontsize_titles,
        )
        generation_flex_activated_plot.set_title(
            "[Generation] x [Generation + Planned/Realised Flex Activation]",
            fontsize=fontsize_titles,
        )
        commitment_costs_plot.set_title(
            "[Commitment Costs Planned X Commitment Costs Realised]",
            fontsize=fontsize_titles,
        )
        cumulative_commitment_costs_plot.set_title(
            "[Cumulative Commitment Costs Planned X Cumulative Commitment Costs Realised]",
            fontsize=fontsize_titles,
        )
        planned_costs_horizons_plot.set_title(
            "[Planned Commitment Deviation Costs]", fontsize=fontsize_titles
        )
        realised_costs_horizons_plot.set_title(
            "[Realised Commitment Deviation Costs]", fontsize=fontsize_titles
        )
        planned_flex_plot.set_title("[Planned Flexibility]", fontsize=fontsize_titles)
        realised_flex_plot.set_title("[Realised Flexibility]", fontsize=fontsize_titles)

        # --------------------- EMS PLOTS -------------------------#
        # EMS PLOT: load profile (check if is curtailable)
        if load_without_flex["derivative equals"].isnull().all():

            flexible_load_lower_bound = load_without_flex["derivative min"]
            flexible_load_upper_bound = load_without_flex["derivative max"]

            net_demand_plot.plot(
                index,
                flexible_load_lower_bound,
                color="blue",
                linestyle="dotted",
                label="Min",
            )
            net_demand_plot.plot(
                index,
                flexible_load_upper_bound,
                color="purple",
                linestyle="dashed",
                alpha=1,
                label="Max",
            )
            net_demand_plot.fill_between(
                index,
                flexible_load_lower_bound,
                flexible_load_upper_bound,
                color="lightblue",
                alpha=0.5,
                label="Activateable",
            )

            load_flex_activated_plot.plot(
                index, flexible_load_lower_bound, color="blue", linestyle="", label=""
            )
            load_flex_activated_plot.plot(
                index, flexible_load_upper_bound, color="blue", linestyle="", label=""
            )
            load_flex_activated_plot.fill_between(
                index,
                flexible_load_lower_bound,
                flexible_load_upper_bound,
                color="lightblue",
                alpha=0.8,
            )
            load_flex_activated_plot.fill_between(
                index,
                flexible_load_lower_bound,
                realised_loads,
                color="red",
                alpha=0.5,
                label="Realised Flex",
            )
            load_flex_activated_plot.plot(
                index,
                realised_loads,
                color="black",
                linestyle="solid",
                linewidth=3,
                label="Realised Load",
            )
            load_flex_activated_plot.plot(
                index,
                planned_loads,
                color="black",
                linestyle="dashed",
                linewidth=3,
                label="Planned Load",
            )
            load_flex_activated_plot.fill_between(
                index,
                planned_loads,
                realised_loads,
                color="indigo",
                alpha=0.2,
                label="Realised - Planned",
            )

            load_without_flex = flexible_load_lower_bound

        else:
            # TODO
            pass

        # # EMS PLOT: generation profile (check if is curtailable)
        if generation_without_flex["derivative equals"].isnull().all():

            full_curtailable_generation = generation_without_flex["derivative min"]

            net_demand_plot.plot(
                index,
                full_curtailable_generation,
                linestyle="dashed",
                color="orange",
                label="Max",
            )
            net_demand_plot.fill_between(
                index,
                0,
                full_curtailable_generation,
                color="orange",
                alpha=0.5,
                label="Curtailable",
            )

            generation_flex_activated_plot.plot(
                index,
                full_curtailable_generation,
                linestyle="dashed",
                color="black",
                label="No Flex",
            )
            generation_flex_activated_plot.fill_between(
                index,
                0,
                full_curtailable_generation,
                color="orange",
                alpha=0.5,
                label="Curtailable",
            )
            generation_flex_activated_plot.fill_between(
                index,
                realised_generation,
                full_curtailable_generation,
                color="red",
                alpha=0.5,
                label="Realised Flex",
            )
            generation_flex_activated_plot.plot(
                index,
                realised_generation,
                color="black",
                linestyle="solid",
                linewidth=3,
                label="Curtailed",
            )
            generation_flex_activated_plot.plot(
                index,
                planned_generation,
                color="black",
                linestyle="",
                linewidth=3,
                label="Curtailed(planned)",
            )
            generation_flex_activated_plot.fill_between(
                index,
                planned_generation,
                realised_generation,
                color="indigo",
                alpha=0.2,
                label="Realised-Planned",
            )
            generation_without_flex = full_curtailable_generation
        else:
            # TODO
            pass

        # EMS PLOT: net demand without flex
        net_demand_without_flex = load_without_flex + generation_without_flex
        net_demand_plot.plot(
            index,
            net_demand_without_flex,
            color="black",
            linewidth=3,
            linestyle="dashed",
            label="No Flex",
        )

        # EMS PLOT: net demand with flex
        net_demand_with_flex = realised_loads + realised_generation
        net_demand_plot.plot(
            index,
            net_demand_with_flex,
            color="black",
            linewidth=3,
            label="Flex activated",
        )
        net_demand_plot.fill_between(
            index,
            net_demand_without_flex,
            net_demand_with_flex,
            color="red",
            alpha=0.5,
            label="Flexibilty",
        )

        realised_flex_plot.bar(
            x=index,
            height=EMS_targeted_flex,
            width=0.01,
            align="edge",
            color="lightgrey",
            alpha=0.5,
            edgecolor="black",
            linewidth=3,
            linestyle="solid",
            label="Flex Request",
        )
        realised_flex_plot.bar(
            x=index,
            height=realised_flex_generation,
            width=0.01,
            align="edge",
            color="orange",
            alpha=0.7,
            linewidth=1,
            linestyle="solid",
            label="Curtailed Generation",
        )
        realised_flex_plot.bar(
            x=index,
            height=realised_flex_loads,
            bottom=realised_flex_generation,
            width=0.01,
            align="edge",
            color="blue",
            alpha=0.7,
            linewidth=1,
            linestyle="solid",
            label="Activated Loads",
        )

        realised_costs_horizons_plot.plot(
            index, realised_costs_horizons.T, marker="o", label="Realised"
        )
        realised_costs_horizons_plot.set_ylabel("Euro", fontsize=y_label_size)

        planned_flex_plot.bar(
            x=index,
            height=EMS_targeted_flex,
            width=0.01,
            align="edge",
            color="lightgrey",
            alpha=0.5,
            edgecolor="black",
            linewidth=3,
            linestyle="solid",
            label="Target Flex",
        )
        planned_flex_plot.bar(
            x=index,
            height=planned_flex_generation,
            width=0.01,
            align="edge",
            color="orange",
            alpha=0.5,
            linewidth=1,
            linestyle="solid",
            label="Curtailed Generation",
        )
        planned_flex_plot.bar(
            x=index,
            height=planned_flex_loads,
            bottom=planned_flex_generation,
            width=0.01,
            align="edge",
            color="blue",
            alpha=0.5,
            linewidth=1,
            linestyle="solid",
            label="Activated Loads",
        )

        planned_costs_horizons_plot.plot(
            index, planned_costs_horizons.T, marker="o", label="Planned"
        )
        planned_costs_horizons_plot.set_ylabel("Euro", fontsize=y_label_size)

        net_demand_costs_without_flex = net_demand_without_flex
        net_demand_costs_without_flex[net_demand_costs_without_flex > 0] = (
            net_demand_without_flex[net_demand_without_flex > 0]
            * environment.ems_agents[0].commitments[0].deviation_cost_curve.gradient_up
        )
        net_demand_costs_without_flex[net_demand_costs_without_flex < 0] = (
            net_demand_without_flex[net_demand_without_flex < 0]
            * environment.ems_agents[0]
            .commitments[0]
            .deviation_cost_curve.gradient_down
        )

        commitment_costs_plot.plot(
            index,
            planned_costs,
            color="blue",
            linewidth=3,
            marker="o",
            markerfacecolor="w",
            markeredgewidth=1.5,
            markeredgecolor="black",
            label="planned_costs",
        )
        commitment_costs_plot.plot(
            index,
            realised_costs,
            color="darkgreen",
            linewidth=3,
            marker="o",
            markerfacecolor="w",
            markeredgewidth=1.5,
            markeredgecolor="black",
            alpha=1,
            label="realised_costs",
        )
        commitment_costs_plot.plot(
            index,
            net_demand_costs_without_flex,
            color="red",
            linewidth=3,
            marker="d",
            markerfacecolor="black",
            markeredgewidth=1.5,
            markeredgecolor="white",
            alpha=1,
            label="net_demand_costs_without_flex",
        )
        commitment_costs_plot.set_ylabel("Euro/kWh", fontsize=y_label_size)

        cumulative_commitment_costs_plot.plot(
            index,
            cum_planned_costs,
            color="mediumblue",
            marker="o",
            markerfacecolor="w",
            markeredgewidth=1.5,
            markeredgecolor="black",
            linewidth=3,
            alpha=1,
            label="Planned",
        )
        cumulative_commitment_costs_plot.plot(
            index,
            cum_realised_costs,
            color="lightgreen",
            marker="o",
            markerfacecolor="w",
            markeredgewidth=1.5,
            markeredgecolor="black",
            linewidth=3,
            alpha=1,
            label="Realised",
        )
        cumulative_commitment_costs_plot.plot(
            index,
            net_demand_costs_without_flex.cumsum(),
            color="red",
            marker="d",
            markerfacecolor="black",
            markeredgewidth=1.5,
            markeredgecolor="black",
            linewidth=3,
            alpha=1,
            label="Realised",
        )

        commitment_costs_plot.set_ylabel("Euro", fontsize=y_label_size)

        # cumulative_commitment_costs_plot.fill_between(index, 0, cum_planned_costs, color="blue", alpha=0.5, label="Planned")
        # cumulative_commitment_costs_plot.fill_between(index, 0, cum_realised_costs, color="forestgreen", alpha=0.8, label="Realised")
        # NET DEMAND CONFIG
        for ax in [
            net_demand_plot,
            generation_flex_activated_plot,
            load_flex_activated_plot,
            planned_flex_plot,
            realised_flex_plot,
        ]:
            ax.set_ylabel("kWh", fontsize=14)
            ax.xaxis.grid(True)
            ax.set_xticks(index)
            ax.set_xticklabels(index, rotation=90)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            # ax.xaxis.set_major_locator(mdates.DayLocator())
            # ax.xaxis.set_minor_formatter(mdates.DateFormatter("%H:%M"))
            ax.axhline(y=0, color="grey")

            # plt.xticks(fontsize=24)
        # Legends
        net_demand_plot.legend(loc="best", ncol=4, fontsize=fontsize_legends)
        load_flex_activated_plot.legend(loc="best", ncol=6, fontsize=fontsize_legends)
        generation_flex_activated_plot.legend(
            loc="best", ncol=3, fontsize=fontsize_legends
        )
        cumulative_commitment_costs_plot.legend(
            loc="best", ncol=1, fontsize=fontsize_legends
        )
        realised_flex_plot.legend(loc="best", ncol=2, fontsize=fontsize_legends)
        planned_flex_plot.legend(loc="best", ncol=2, fontsize=fontsize_legends)
        commitment_costs_plot.legend(loc="best", ncol=2, fontsize=fontsize_legends)
        cumulative_commitment_costs_plot.legend(
            loc="best", ncol=2, fontsize=fontsize_legends
        )

        # for ax in [ma_imbalance_market_prices_plot,ma_requested_flex_plot, ma_imbalance_market_costs_plot,ma_deviation_prices_plot]:
        for ax in [
            cumulative_commitment_costs_plot,
            commitment_costs_plot,
            planned_costs_horizons_plot,
            realised_costs_horizons_plot,
        ]:
            ax.xaxis.grid(True)
            ax.set_xticks(index)
            ax.set_xticklabels(index, rotation=90)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax.xaxis.grid(True)
            ax.axhline(y=0, color="grey")
        # plt.tight_layout()
        plt.savefig("EMS_Data.pdf", transparent=True, quality=100, frameon=False)


def plot_ma_data(environment):

    # Plot config
    fontsize_titles = 14
    fontsize_titles = 16
    fontsize_legends = 13
    y_label_size = 14

    start = environment.start
    end = environment.end
    resolution = environment.resolution

    # plt.rcParams['axes.xmargin'] = 0
    plt.figure(figsize=(20, 25))
    plt.rcParams["axes.xmargin"] = 0
    ticklabel_size = 14
    mpl.rcParams["xtick.labelsize"] = ticklabel_size
    mpl.rcParams["ytick.labelsize"] = ticklabel_size
    # Create subplots

    gs = gridspec.GridSpec(5, 1, height_ratios=[1, 1, 1, 1, 1])
    gs.update(wspace=0.15, hspace=0.35)

    cut_off_indices = int(environment.max_horizon / resolution - 1)
    index = environment.simulation_runtime_index[:-cut_off_indices]

    # Load profile data MA
    ma_negotiated_flex = environment.market_agent.commitments["negotiated_flex"].apply(
        to_numeric, errors="ignore"
    )
    ma_requested_flex = environment.market_agent.balancing_opportunities[
        "Imbalance (in MW)"
    ].apply(to_numeric, errors="ignore")
    ma_imbalance_market_prices = environment.market_agent.balancing_opportunities[
        "Price (in EUR/MWh)"
    ].apply(to_numeric, errors="ignore")
    ma_imbalance_market_costs = environment.market_agent.imbalance_market_costs.apply(
        to_numeric, errors="ignore"
    )
    ma_received_flexibility = environment.market_agent.commitments[
        "received_flex"
    ].apply(to_numeric, errors="ignore")
    ma_deviation_prices = Series(
        data=environment.market_agent.deviation_prices_realised, index=index
    )
    ma_unfulfilled_flex = (
        environment.market_agent.commitments["requested_flex"]
        - environment.market_agent.commitments["received_flex"]
    )

    ma_deviation_prices = ma_deviation_prices[start : end - environment.max_horizon]
    ma_requested_flex = ma_requested_flex[:-cut_off_indices]
    ma_negotiated_flex = ma_negotiated_flex[:-cut_off_indices]
    ma_received_flex = ma_received_flexibility[:-cut_off_indices]
    ma_imbalance_market_prices = ma_imbalance_market_prices[:-cut_off_indices]
    ma_imbalance_market_costs = ma_imbalance_market_costs[
        start : end - environment.max_horizon
    ]

    ma_imbalance_market_cost_normalized = (
        ma_imbalance_market_costs / ma_imbalance_market_costs.max()
    )
    ma_imbalance_market_cost_normalized = ma_imbalance_market_cost_normalized[
        start : end - environment.max_horizon
    ]
    ma_unfulfilled_flex = ma_unfulfilled_flex[start : end - environment.max_horizon]
    ma_unfulfilled_flex_costs = (
        abs(ma_unfulfilled_flex)
        * ma_imbalance_market_prices[start : end - environment.max_horizon]
    )

    # Subplots MA
    ma_imbalance_market_prices_plot = plt.subplot(gs[0, :])
    ma_imbalance_market_costs_plot = plt.subplot(gs[1, :])
    ma_cumulative_market_costs_plot = plt.subplot(gs[2, :])
    ma_requested_flex_plot = plt.subplot(gs[3, :])
    ma_deviation_prices_plot = plt.subplot(gs[4, :])

    # # --------------------- CONFIG -------------------------#

    # TITLES
    ma_imbalance_market_prices_plot.set_title(
        "MA: [Imbalance Market Prices Plot]", fontsize=fontsize_titles
    )
    ma_imbalance_market_costs_plot.set_title(
        "MA: [Imbalance Market Costs ]", fontsize=fontsize_titles
    )
    ma_cumulative_market_costs_plot.set_title(
        "MA: [Cumulative Imbalance Market Costs]", fontsize=fontsize_titles
    )
    ma_requested_flex_plot.set_title(
        "MA: [Requested, Negotiated And Agreed Flex Activation]",
        fontsize=fontsize_titles,
    )
    ma_deviation_prices_plot.set_title(
        "MA:[Deviation Prices]", fontsize=fontsize_titles
    )
    # --------------------- MA PLOTS -------------------------#
    ma_imbalance_market_prices_plot.plot(
        index,
        ma_imbalance_market_prices,
        color="black",
        linewidth=3,
        label="Expected Market Prices",
    )
    ma_imbalance_market_prices_plot.plot(
        index,
        ma_imbalance_market_prices * 1.8,
        color="blue",
        linewidth=3,
        linestyle=":",
        label="Expected UB",
    )
    ma_imbalance_market_prices_plot.plot(
        index,
        ma_imbalance_market_prices * 0.6,
        color="blue",
        linewidth=3,
        linestyle=":",
        label="Expected LB",
    )

    ma_imbalance_market_prices_plot.plot(
        index,
        ma_deviation_prices / 4,
        color="red",
        linewidth=3,
        linestyle="dashed",
        label="Deviations Prices",
    )

    ma_imbalance_market_prices_plot.set_ylabel("Euro/kWh", fontsize=y_label_size)

    ma_imbalance_market_costs_plot.plot(
        index,
        ma_imbalance_market_costs,
        color="black",
        linewidth=3,
        linestyle="solid",
        label="Market Costs",
    )
    ma_imbalance_market_costs_plot.plot(
        index,
        ma_unfulfilled_flex_costs,
        color="black",
        linewidth=3,
        linestyle="dashed",
        label="Reduced Costs",
    )
    ma_imbalance_market_costs_plot.fill_between(
        index, 0, ma_imbalance_market_costs, color="black", alpha=0.45, label=""
    )
    ma_imbalance_market_costs_plot.fill_between(
        index,
        0,
        ma_unfulfilled_flex_costs,
        color="red",
        alpha=0.55,
        label="Remaining Market Costs",
    )
    ma_imbalance_market_costs_plot.set_ylabel("Euro", fontsize=y_label_size)

    ma_cumulative_market_costs_plot.plot(
        index,
        ma_imbalance_market_costs.cumsum(),
        color="black",
        marker="o",
        linewidth=3,
        linestyle="solid",
        label="Market Costs",
    )
    ma_cumulative_market_costs_plot.plot(
        index,
        ma_unfulfilled_flex_costs.cumsum(),
        color="red",
        marker="o",
        linewidth=3,
        linestyle="solid",
        label="Market Costs with Flex Activation",
    )
    ma_cumulative_market_costs_plot.set_ylabel("Euro", fontsize=y_label_size)

    ma_deviation_prices_plot.plot(
        ma_deviation_prices,
        linewidth=1,
        linestyle="solid",
        marker="o",
        label="Deviation Prices positiv",
    )
    ma_deviation_prices_plot.fill_between(
        index, 0, ma_deviation_prices, alpha=0.65, label=""
    )
    ma_deviation_prices_plot.plot(
        -ma_deviation_prices,
        linewidth=1,
        linestyle="solid",
        marker="o",
        label="Deviation Prices negativ",
    )
    ma_deviation_prices_plot.fill_between(
        index, 0, -ma_deviation_prices, alpha=0.65, label=""
    )
    ma_deviation_prices_plot.set_ylabel("Euro/kWh", fontsize=y_label_size)

    ma_requested_flex_plot.bar(
        x=index,
        height=ma_requested_flex,
        width=0.01,
        align="edge",
        facecolor="white",
        alpha=0.5,
        edgecolor="black",
        linewidth=2,
        linestyle="solid",
        label="Requested Flex",
    )
    ma_requested_flex_plot.bar(
        x=index,
        height=ma_unfulfilled_flex,
        width=0.01,
        align="edge",
        facecolor="red",
        alpha=0.7,
        edgecolor="black",
        bottom=ma_received_flex,
        linewidth=1,
        linestyle="solid",
        label="Unfulfilled Flex",
    )
    ma_requested_flex_plot.bar(
        x=index,
        height=ma_negotiated_flex,
        width=0.01,
        align="edge",
        facecolor="purple",
        alpha=1,
        edgecolor="black",
        linewidth=1,
        linestyle="solid",
        label="Flex No Agreement",
    )
    ma_requested_flex_plot.bar(
        x=index,
        height=ma_received_flex,
        width=0.01,
        align="edge",
        facecolor="black",
        alpha=0.5,
        edgecolor="black",
        linewidth=1,
        linestyle="solid",
        label="Flex Agreement",
    )
    ma_requested_flex_plot.set_ylabel("kWh", fontsize=y_label_size)

    for ax in [
        ma_imbalance_market_prices_plot,
        ma_requested_flex_plot,
        ma_imbalance_market_costs_plot,
        ma_deviation_prices_plot,
        ma_cumulative_market_costs_plot,
    ]:
        ax.xaxis.grid(True)
        ax.set_xticks(index)
        ax.set_xticklabels(index, rotation=90)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        # ax.xaxis.set_major_locator(mdates.DayLocator())
        # ax.xaxis.set_minor_formatter(mdates.DateFormatter("%H:%M"))
        ax.axhline(y=0, color="grey")

    # Legends

    ma_imbalance_market_prices_plot.legend(
        loc="best", ncol=2, fontsize=fontsize_legends
    )
    ma_requested_flex_plot.legend(loc="best", ncol=2, fontsize=fontsize_legends)
    ma_imbalance_market_costs_plot.legend(loc="best", ncol=2, fontsize=fontsize_legends)
    ma_deviation_prices_plot.legend(loc="best", ncol=2, fontsize=fontsize_legends)
    ma_deviation_prices_plot.legend(loc="best", ncol=2, fontsize=fontsize_legends)
    ma_cumulative_market_costs_plot.legend(
        loc="best", ncol=2, fontsize=fontsize_legends
    )
    plt.savefig("MA_Data.pdf", transparent=True)

    return plt
