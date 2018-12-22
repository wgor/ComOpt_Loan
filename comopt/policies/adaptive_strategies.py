from typing import List, Optional, Union, Tuple, Callable
from random import uniform, gauss, seed, randint
from copy import deepcopy
from numpy import abs, sin
from pandas import DataFrame
# from comopt.model.negotiation_utils import (
#     root_divided_by_2,
#     linear,
#     cos_root_divided_by_2,
#     no_shape,
#     gauss_1,
#     gauss_2,
#     uniform_1,
#     no_noise,
# )
from functools import wraps

"""Policy functions configures the strategy arguments for agents within negotiations"""

# Decorator for exploration functions
def exploration_function(exploration_function: Callable) -> Callable:

    @wraps(exploration_function)
    def exploration_function_wrapper(
        q_table: DataFrame, ta_parameter: dict, round_now: int
    ):
        return exploration_function(
            q_table=q_table, ta_parameter=ta_parameter, round_now=round_now
        )

    return exploration_function_wrapper


# Decorator for action functions
def action_function(action_function: Callable) -> Callable:
    @wraps(action_function)
    def action_function_wrapper(action: str, markup: float, show_actions: bool):
        # TODO: Test for exceptions
        # show_actions argument allows to return only the actions specified in a given action function, used to e.g. to set up q-table
        if show_actions == True:
            return action_function(
                action=action, markup=markup, show_actions=show_actions
            )["Actions"]

        else:
            return action_function(action=action, markup=markup, show_actions=False)[
                "Markup"
            ]

    return action_function_wrapper


# ---------------------------------- DECORATED EXPLORATION FUNCTIONS ----------------------------------------#
@exploration_function
# Randomizes existing Q-table with decaying noise (-> 1/environment.step_now). Action then gets chosen based on max Q-values of the randomized table.
def choose_action_greedily_with_noise(
    q_table: DataFrame, ta_parameter: dict, round_now: int
) -> str:

    # Make copy of Q-Table
    randomized_table = deepcopy(q_table)
    # Get number of possible actions
    number_of_actions = len(
        ta_parameter["Action function"](
            action=None, markup=None, show_actions=True
        ).keys()
    )

    # Randomize Q-value(=value) for each action(=column) in round_now(=index)
    for col in q_table.columns:
        randomized_table.loc[round_now, col] = q_table.loc[round_now, col] + randint(
            1, number_of_actions
        ) * (1. / (ta_parameter["Step now"]))

    # Get column name of max Q-value from randomized Q-Table
    action = randomized_table.loc[round_now, :].idxmax(axis=1)

    return action


@exploration_function
# If uniform(0,1) gives a number above q_parameter["Epsilon"], agent uses random action sampling. Otherwise the action with max Q-Value gets selected.
def choose_action_randomly_using_uniform(
    q_table: DataFrame, ta_parameter: dict, round_now: int
) -> str:

    # Random selection
    if uniform(0, 1) > ta_parameter["Epsilon"]:
        action = q_table.loc[round_now, :].sample(1)
        return action.index.format()[0]

    # Greedy selection
    else:
        action = q_table.loc[round_now, :].idxmax()

        return action


# ---------------------------------- DECORATED ACTION FUNCTIONS ----------------------------------------#
@action_function
# Action function for learning based policies
def multiply_markup_evenly(
    action: str, markup: float, show_actions: bool = False
) -> float:

    # Describe actions and action values here
    actions = {
        "+75": 1.75,
        "+50": 1.5,
        "+25": 1.25,
        "0": 1,
        "-25": 0.75,
        "-50": 0.5,
        "-75": 0.25,
    }

    # If called only for the action names, make sure you pass markup = None to the action functions arguments.
    if markup is not None:
        markup = markup * actions[action]

    return {"Markup": markup, "Actions": actions}
