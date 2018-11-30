import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from pandas import DataFrame
import numpy as np
from numpy import exp, poly1d, polyfit, unique, asarray


def plot_negotiation_data(input_data: dict, negotiation_data_df: DataFrame, q_tables: dict = None, action_tables: dict = None):
    # Figure layout parameter
    plt.rcParams["figure.figsize"] = [40,80]
    gs = gridspec.GridSpec(12,4, height_ratios=[2, 1.5, 1.5, 1, 1, 1, 1, 1, 1, 1, 1, 0.75], width_ratios=[1,1,1,1])
    gs.update(wspace=0.25, hspace=0.4)

    # Dummy variables
    df=negotiation_data_df
    rounds_index = negotiation_data_df.index.get_level_values("Round").unique()
    datetime_index = negotiation_data_df.index.get_level_values("Datetime").unique()
    clearing_price_mean = df["Clearing price"].groupby("Round").sum()/df["Cleared"].groupby("Round").sum()
    ta_bids_mean = df["TA bid"].groupby("Round").sum()/df["TA bid"].groupby("Round").count()
    ma_bids_mean = df["MA bid"].groupby("Round").sum()/df["MA bid"].groupby("Round").count()
    ta_mean_profit = [df.groupby(["Round"]).get_group(round)["TA profit"].sum()/
                      df.groupby(["Round"]).get_group(round)["Cleared"].sum()
                      if df.groupby(["Round"]).get_group(round)["Cleared"].sum() > 0 else 0
                      for round in rounds_index]
    ma_mean_profit = [df.groupby(["Round"]).get_group(round)["MA profit"].sum()/
                      df.groupby(["Round"]).get_group(round)["Cleared"].sum()
                      if df.groupby(["Round"]).get_group(round)["Cleared"].sum() > 0 else 0
                      for round in rounds_index]
    total_profit_MA = round(df.groupby(["Datetime"])["MA profit"].sum().sum(),2)
    total_profit_TA = round(df.groupby(["Datetime"])["TA profit"].sum().sum(),2)
    total_number_of_clearings = [e for e in enumerate(datetime_index, start=1)]
    cleared_rounds_cumulated = df.groupby(["Datetime"])["Cleared"].sum().cumsum()
    ratio = df[df["Cleared"] > 0]["Cleared"].sum()/len(total_number_of_clearings)*100

    fontsize_titles = 14
    # ax0 Bidding per round
    ax0 = plt.subplot(gs[0,:])
    ax0.set_title("Number of Negotiatons: {}, Rounds each: {}".format(len(datetime_index),len(rounds_index)),
                  fontsize=fontsize_titles)

    # ax1 Bidding Acceptance Range per round
    ax1 = plt.subplot(gs[1,:])
    ax1.set_ylim(df.groupby(["Round"]).get_group(1)["TA reservation price"][0],
                 df.groupby(["Round"]).get_group(1)["MA reservation price"][0]
                 )
    ax1.set_xticks(rounds_index)
    ax1.set_title("Reservation price range", fontsize=fontsize_titles)

    # ax2 Average Bids per round
    ax2 = plt.subplot(gs[2,:])
    ax2.set_title("Averaged bid and clearing price values per round", fontsize=fontsize_titles)

    # ax3 Average Profits per round + number of clearings per round
    ax31 = plt.subplot(gs[3,0:2])
    ax31.set_title("Clearings and AVG bids per round and agent",fontsize=fontsize_titles)
    ax32 = ax31.twinx()
    ax32.tick_params(axis=0, direction="in", left=True)
    bar_width = 0.15

    # ax4 Boxplot Clearing prices per round
    ax4 = plt.subplot(gs[3,2:4])
    ax4.set_title("Clearing prices per round", fontsize = fontsize_titles)

    # ax5 Cumulated Profits
    ax5 = plt.subplot(gs[4,0:2])
    ax5.set_title("Cumulated Profits over runtime", fontsize = fontsize_titles)
    ax5.set_ylabel('Euro', fontsize=15)
    ax5.xaxis.grid(True)

    # ax6 Boxplot TA Bids per round
    ax6 = plt.subplot(gs[4,2:4])
    ax6.set_title("TA Bids per round", fontsize = fontsize_titles)

    # ax7 Cumulated Clearings
    ax7 = plt.subplot(gs[5,0:2])
    ax7.set_title("Cumulated Clearings over runtime", fontsize = fontsize_titles)
    ax7.xaxis.grid(True)
    ax7.set_ylabel('Clearings', fontsize=15)
    ax7.set_ylim(0, len(datetime_index)+5)

    # ax8 Boxplot MA Bids per round
    ax8 = plt.subplot(gs[5,2:4])
    ax8.set_title("MA Bids per round", fontsize = fontsize_titles)

    # ax9 TA Profit(Markup)
    ax9 = plt.subplot(gs[6,0:2])
    ax9.set_title("TA Profit x TA Markup", fontsize = fontsize_titles)
    ax9.xaxis.grid(True)
    ax9.set_xlabel('Markup in Euro', fontsize=15)
    ax9.set_ylabel('Profit in Euro', fontsize=15)

    # ax10 MA Profit(Markup)
    ax10 = plt.subplot(gs[6,2:4])
    ax10.set_title("MA Profit x MA Markup", fontsize = fontsize_titles)
    ax10.xaxis.grid(True)
    ax10.set_xlabel('Markup in Euro', fontsize=15)
    ax10.set_ylabel('Profit in Euro', fontsize=15)

    # ax10 Heatplots Q-Values per quarter of simulation horizon
    ax11 = plt.subplot(gs[7,0:1])
    ax12 = plt.subplot(gs[7,1:2])
    ax13 = plt.subplot(gs[7,2:3])
    ax14 = plt.subplot(gs[7,3:4])
    ax15 = plt.subplot(gs[8,0:1])
    ax16 = plt.subplot(gs[8,1:2])
    ax17 = plt.subplot(gs[8,2:3])
    ax18 = plt.subplot(gs[8,3:4])

    ax19 = plt.subplot(gs[9,0:1])
    ax20 = plt.subplot(gs[9,1:2])
    ax21 = plt.subplot(gs[9,2:3])
    ax22 = plt.subplot(gs[9,3:4])
    ax23 = plt.subplot(gs[10,0:1])
    ax24 = plt.subplot(gs[10,1:2])
    ax25 = plt.subplot(gs[10,2:3])
    ax26 = plt.subplot(gs[10,3:4])

    # Table output
    ax27 = plt.subplot(gs[11,0:4])
    ax27.set_yticklabels(invisible=True, labels="")
    ax27.set_xticklabels(invisible=True, labels="")
    try:
        legend_elements_ax27  = [
                                Line2D([0], [0], linestyle='', label='MA policy: {}'.format(input_data["MA prognosis policy"].__name__)),
                                Line2D([0], [0], linestyle='', label='TA policy: {}'.format(input_data["TA prognosis policy"].__name__)),
                                Line2D([0], [0], linestyle='', label='Exploration: {}'.format(input_data["Q parameter prognosis"]["Exploration function"].__name__)),
                                Line2D([0], [0], linestyle='', label='Action: {}'.format(input_data["Q parameter prognosis"]["Action function"].__name__)),
                                Line2D([0], [0], linestyle='', label='Alpha: {}'.format(input_data["Q parameter prognosis"]["Alpha"])),
                                Line2D([0], [0], linestyle='', label='Gamma: {}'.format(input_data["Q parameter prognosis"]["Gamma"])),
                                Line2D([0], [0], linestyle='', label='Epsilon: {}'.format(input_data["Q parameter prognosis"]["Epsilon"])),
                                Line2D([0], [0], linestyle='', label='Seed: {}'.format(input_data["Seed"])),

                                ]
    except:
        pass
    ax27.set_xticklabels(invisible=True, labels="")
    ax27.legend(handles=legend_elements_ax27, fontsize=15, loc="center", ncol=2)
    try:
        # Heatmap plots
        heatmaps = [ax11, ax12, ax13, ax14, ax15, ax16, ax17, ax18]
        # TODO: Implement better loop here
        for table, ax in zip(list(q_tables.items()), heatmaps):
            im = ax.imshow(table[1].transpose())
            ax.set_title("Environment runtime: {} %".format( round(100*table[0][0]/(len(datetime_index)) ), fontsize = 12))
            ax.set_xticks(np.arange(len(table[1].index)))
            ax.set_yticks(np.arange(len(table[1].columns)))
            ax.set_yticklabels(table[1].columns)
            ax.set_xticklabels(["R {}:".format(i) for i in table[1].index])
            cbar = ax.figure.colorbar(im, ax=ax)

            #ax.margins(x=0, y=0.5)
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

            for i in range(len(table[1].index)):
                for j in range(len(table[1].columns)):
                    ax.text(j, i, "", ha="center", va="center", color="w")

        heatmaps = [ax19, ax20, ax21, ax22, ax23, ax24, ax25, ax26]
        for table, ax in zip(list(action_tables.items()), heatmaps):
            im = ax.imshow(table[1].transpose(), cmap="Greens")
            ax.set_title("Environment runtime: {} %".format( round(100*table[0][0]/(len(datetime_index)) ), fontsize = 12))
            ax.set_xticks(np.arange(len(table[1].index)))
            ax.set_yticks(np.arange(len(table[1].columns)))
            ax.set_yticklabels(table[1].columns)
            ax.set_xticklabels(["R {}:".format(i) for i in table[1].index])
            cbar = ax.figure.colorbar(im, ax=ax)
            #ax.margins(x=0, y=0.5)
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

            for i in range(len(table[1].index)):
                for j in range(len(table[1].columns)):
                    ax.text(j, i, "", ha="center", va="center", color="w")

        for ax in [ax0,ax1,ax2,ax31,ax4,ax6,ax8]:
            ax.xaxis.grid(True)
            ax.set_xticks(rounds_index)
            ax.set_ylabel('Euro', fontsize=15)
            plt.xticks(fontsize=14, rotation=0)
            plt.yticks(fontsize=14, rotation=0)

        # ax0 + ax1
        for ax in [ax0,ax1]:
            for datetime in datetime_index:
                ax.plot(rounds_index, "MA bid", data=df.groupby(["Datetime"]).get_group(datetime),
                         marker='X', markerfacecolor='lightblue', markersize=8, linestyle='None')

                ax.plot(rounds_index, "TA bid", data=df.groupby(["Datetime"]).get_group(datetime),
                         marker='D', markerfacecolor='lightgreen', markersize=8,
                         markeredgecolor="black", markeredgewidth=1.5, linestyle='None')

                ax.plot(rounds_index, "MA reservation price", data=df.groupby(["Datetime"]).get_group(datetime),
                        color='dodgerblue', linewidth=3, linestyle='dashed')

                ax.plot(rounds_index, "TA reservation price", data=df.groupby(["Datetime"]).get_group(datetime),
                         color='forestgreen', linewidth=2, linestyle='-.')

                ax.plot(rounds_index, "Clearing price", data=df.groupby(["Datetime"]).get_group(datetime),
                         marker='o', markerfacecolor='red', markersize=14, alpha=0.3, linestyle='None')
    except:
        pass

    legend_elements_ax1  = [Line2D([0], [0], color="dodgerblue", linestyle='dashed', label='MA res'),
                            Line2D([0], [0], color="forestgreen", linestyle='-.', label='TA res'),
                            Line2D([0], [0], marker='x', markerfacecolor='black', markersize=10, linestyle='None', label='MA bid'),
                            Line2D([0], [0], marker='D', markerfacecolor='black', markersize=8, linestyle='None', label='TA bid'),
                            Line2D([0], [0], marker='o', markerfacecolor='red', markersize=16, label='Clearing')]

    ax0.legend(handles=legend_elements_ax1, fontsize=15, loc="lower right")

    # ax2: Averaged bids and number of clearings per round
    ax2.plot(rounds_index, clearing_price_mean,
             marker='o', markerfacecolor='Red', markeredgecolor="black", markeredgewidth=1, markersize=8, alpha=0.5,
             lw=5, linestyle='-', color='Red', label="Clearing price")
    ax2.plot(rounds_index, ta_bids_mean,
             #marker='', markerfacecolor='Red', markeredgecolor="black",markeredgewidth=2, markersize=10,
             lw=3, linestyle='-', color='Green', alpha=0.7, label="TA Bids avg")
    ax2.plot(rounds_index, ma_bids_mean,
             #marker='', markerfacecolor='Red', markeredgecolor="black",markeredgewidth=2, markersize=10,
             lw=3, linestyle='-', color='Blue', alpha=0.7, label="MA Bids avg")

    ax2.legend(loc='best', fancybox=True, ncol=3, fontsize=14 , framealpha=0.8)

    # ax3 Average Profits
    ax31.bar(x=rounds_index-bar_width, height=ta_mean_profit,
            width=bar_width, color='white', edgecolor="forestgreen", lw=3, label='TA')
    ax31.bar(x=rounds_index+bar_width, height=ma_mean_profit,
            width=bar_width, color='white', edgecolor="dodgerblue", lw=3, label='MA')
    ax32.bar(x=rounds_index, height=[df.groupby(["Round"]).get_group(round)["Cleared"].sum() for round in rounds_index],
            width=bar_width, color='black', edgecolor="", lw=3, label='Clearings')

    ax31.legend(loc='upper left', fancybox=True, ncol=3, fontsize=14, framealpha=0.8)
    ax32.legend(bbox_to_anchor=(0.45, 1), fancybox=True, ncol=3, fontsize=14, framealpha=0.8)

    # ax4: Clearing price distributions
    clearing_boxes = [df.groupby(["Round"]).get_group(round)["Clearing price"].dropna() for round in rounds_index]
    clearing_boxes = [list(box.values.flatten()) for box in clearing_boxes]
    bp = ax4.boxplot([x for x in clearing_boxes], positions = rounds_index,
                      patch_artist = True, widths = 0.25)

    for box, median in zip(bp['boxes'],bp['medians']):
        box.set(color='red', linewidth=1,  facecolor = 'red')
        median.set(color="black", linewidth=1)

    # ax5: Cumulated profits
    ax5.plot(datetime_index, df.groupby(["Datetime"])["MA profit"].sum().cumsum(),
            marker='+', markerfacecolor='black',
            color='dodgerblue', label="MA cum profit")

    ax5.plot(datetime_index, df.groupby(["Datetime"])["TA profit"].sum().cumsum(),
            color='forestgreen', linestyle="dashed", label="TA cum profit")

    legend_elements_ax5  = [Line2D([0], [0], color="dodgerblue", linestyle='-', label='MA Profits: {}'.format(round(total_profit_MA))),
                            Line2D([0], [0], color="forestgreen", linestyle="dashed", label='TA Profits: {}'.format(round(total_profit_TA))),
                            Line2D([0], [0], color="", linestyle='', label='TA profits %: {}'.format(round(total_profit_TA / (total_profit_MA+total_profit_TA) * 100,2))),
                            Line2D([0], [0], color="", linestyle='', label='MA profits %: {}'.format(round(total_profit_MA / (total_profit_MA+total_profit_TA) * 100,2))),
                            ]

    ax5.legend(handles=legend_elements_ax5,loc = 'best', fontsize=14)

    # ax6: Boxplot TA bids
    ta_bid_boxes = [df.groupby(["Round"]).get_group(round)["TA bid"].dropna() for round in rounds_index]
    ta_bid_boxes = [list(box.values.flatten()) for box in ta_bid_boxes]
    bp = ax6.boxplot([x for x in ta_bid_boxes], positions = rounds_index,
                      patch_artist = True, widths = 0.25)

    for box, median in zip(bp['boxes'],bp['medians']):
        # change outline color
        box.set( color='black', linewidth=1)
        # change fill color
        box.set( facecolor = 'lightblue')
        median.set(color="black", linewidth=1)

    # ax7: Cumulated clearings
    ax7.plot(datetime_index, cleared_rounds_cumulated,
            marker='', markerfacecolor='black',
            linestyle='-',color='Black', label="Cleared Rounds")

    ax7.plot(datetime_index, total_number_of_clearings,
            marker='', markerfacecolor='black',
            linestyle='dashed', color='red', label="Total Rounds")

    legend_elements_ax7  = [Line2D([0], [0], color="red", linestyle='dashed', label='Total number of Clearings: {}'.format(len(total_number_of_clearings))),
                            Line2D([0], [0], color="black", linestyle='-', label='Cleared rounds: {}'.format(df[df["Cleared"] > 0]["Cleared"].sum())),
                            Line2D([0], [0], linestyle='None', label='Cleared: {} %:'.format(round(ratio,2))),
                            ]
    ax7.legend(handles=legend_elements_ax7, fontsize=15, loc="best")

    # ax8: Boxplot MA bids
    ma_bid_boxes = [df.groupby(["Round"]).get_group(round)["MA bid"].dropna() for round in rounds_index]
    ma_bid_boxes = [list(box.values.flatten()) for box in ma_bid_boxes]
    bp = ax8.boxplot([x for x in ma_bid_boxes], positions = rounds_index,
                      patch_artist = True, widths = 0.25)

    for box, median in zip(bp['boxes'],bp['medians']):
        # change outline color
        box.set( color='black', linewidth=1)
        # change fill color
        box.set( facecolor = 'lightgreen')
        median.set(color="black", linewidth=1)

    # ax9: Scatter TA Profit(Markup)
    x=asarray(df[df["TA profit"] > 0]["TA markup"], dtype=float)
    y=asarray(df[df["TA profit"] > 0]["TA profit"], dtype=float)
    ax9.scatter(x=x, y=y, marker='o', color='forestgreen', linewidths=4, label="Profit(Markup)")

    # ax10: Scatter TA Profit(Markup)
    x=asarray(df[df["MA profit"] > 0]["MA markup"], dtype=float)
    y=asarray(df[df["MA profit"] > 0]["MA profit"], dtype=float)
    ax10.scatter(x=x, y=y, marker='X', color='blue', linewidths=4, label="Profit(Markup)")

    plt.savefig("Flex_Negotiation.pdf", transparent= True)
    # Legends

    return plt
