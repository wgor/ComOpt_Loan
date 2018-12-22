from typing import List, Optional, Union, Tuple, Callable
from random import uniform, gauss, seed, randint
from copy import deepcopy
from numpy import abs, sin
from pandas import DataFrame
from functools import wraps

from comopt.model.negotiation_utils import (
    root_divided_by_2,
    linear,
    cos_root_divided_by_2,
    no_shape,
    gauss_1,
    gauss_2,
    uniform_1,
    no_noise,
)

from comopt.policies.adaptive_strategies import (
    exploration_function,
    action_function,
    choose_action_greedily_with_noise,
    choose_action_randomly_using_uniform,
    multiply_markup_evenly,
)

from comopt.model.plan_board import PlanBoard

"""Policy functions configures the strategy arguments for agents within negotiations"""

# ---------------------------------- DECORATORS ----------------------------------------#
# Decorator function for distribution sampling based policies
def get_TA_bid_from_sample(policy_function: Callable) -> Callable:
    @wraps(policy_function)
    # @wraps is a helper function that allows to keep policy functions name when calling e.g. sell_at_any_cost.__name__
    def policy_function_wrapper(
        rounds_total: int,
        rounds_left: int,
        ta_parameter: dict,
        q_table_df: DataFrame,
        q_parameter: dict,
    ) -> dict:

        # Get return values from wrapped policy function -> dict()
        ta = policy_function(
            rounds_total=rounds_total,
            rounds_left=rounds_left,
            ta_parameter=ta_parameter,
            q_table_df=q_table_df,
            q_parameter=q_parameter,
        )

        # Modify shaped markup based on choosen exploration function
        ta["Markup"] = (
            ta["Markup"]
            + ta["Noise"](
                rounds_total=rounds_total, rounds_left=rounds_left, mean=ta["Markup"]
            )
        ) * ta["Concession"](rounds_total=rounds_total, rounds_left=rounds_left)
        ta["Bid"] = ta["Reservation price"] + ta["Markup"]

        # If TAs bid is lower than his reservation price, use reservation price instead
        if ta["Bid"] < ta["Reservation price"]:
            ta["Bid"] = ta["Reservation price"]

        return {
            "Bid": ta["Bid"],
            "Reservation price": ta["Reservation price"],
            "Markup": ta["Markup"],
            "Q_Table": None,
            "Q_Parameter": q_parameter,
            "Action": None,
        }

    return policy_function_wrapper


# Decorator function for learning based policies
def get_TA_bid_from_learning(policy_function: Callable) -> Callable:

    # @wraps allows to keep the object properties of the wrapped functions (e.g. sell_at_any_cost.__name__)
    @wraps(policy_function)

    def policy_function_wrapper(
        description: str,
        ta_parameter: dict,
        plan_board: PlanBoard,
        rounds_total: int,
        rounds_left: int,
    ) -> dict:

        # Get return values from wrapped policy function -> dict()
        ta = policy_function(
            description=description,
            ta_parameter=ta_parameter,
            plan_board=plan_board,
            rounds_total=rounds_total,
            rounds_left=rounds_left,
        )

        return {
            "Bid": ta["Bid"],
            "Reservation price": ta["Reservation price"],
            "Markup": ta["Markup"],
            "Action": ta["Action"],
        }

    return policy_function_wrapper

# ------------------------------ DECORATED SAMPLING POLICY FUNCTIONS ------------------------------------#
@get_TA_bid_from_sample
# Selling with a reservation price of +inf
def never_sell(
    rounds_total_total: int,
    rounds_left: int,
    reservation_price=float("inf"),
    markup: Union[int, float] = 1,
    q_table_df: DataFrame = None,
    q_parameter: dict = None,
) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {
        "Bid": 0,
        "Reservation price": reservation_price,
        "Markup": markup,
        "Shape": concession_curve,
        "Q_Table": None,
        "Q_Parameter": q_parameter,
        "Action": None,
    }


# TODO: Testing needed. Probably implementing try-functions.
# Selling with a reservation price and markup of 0
@get_TA_bid_from_sample
def sell_at_any_cost(
    rounds_total: int,
    rounds_left: int,
    reservation_price=0,
    markup: Union[int, float] = 0,
    concession_curve: Union[root_divided_by_2, linear, no_shape] = linear,
    q_table_df: DataFrame = None,
    q_parameter: dict = None,
) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {
        "Bid": 0,
        "Reservation price": reservation_price,
        "Markup": markup,
        "Shape": concession_curve,
        "Q_Table": None,
        "Q_Parameter": q_parameter,
        "Action": None,
    }


@get_TA_bid_from_sample
# Deterministic markup prices
def sell_with_deterministic_prices(
    rounds_total: int,
    rounds_left: int,
    q_table_df: DataFrame,
    q_parameter: dict,
    reservation_price: Union[int, float] = 2,
    markup: Union[int, float] = 0.5,
    concession_curve: Union[root_divided_by_2, linear, no_shape] = linear,
) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {
        "Bid": 0,
        "Reservation price": reservation_price,
        "Markup": markup,
        "Shape": concession_curve,
        "Q_Table": None,
        "Q_Parameter": q_parameter,
        "Action": None,
    }


@get_TA_bid_from_sample
# Samples markup prices from distribution
def sell_with_stochastic_prices(
    rounds_total: int,
    rounds_left: int,
    q_table_df: DataFrame,
    q_parameter: dict,
    ta_parameter: dict,
) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {
        "Bid": 0,
        "Reservation price": ta_parameter["Reservation price"],
        "Markup": ta_parameter["Markup"],
        "Concession": ta_parameter["Concession"],
        "Noise": ta_parameter["Noise"],
        "Q_Table": None,
        "Q_Parameter": q_parameter,
        "Action": None,
    }


# ------------------------------ DECORATED LEARNING POLICY FUNCTIONS ------------------------------------#
@get_TA_bid_from_learning
# Gets prices based on q-learning
def Q_learning(
    description: str,
    ta_parameter: dict,
    plan_board: PlanBoard,
    rounds_total: int,
    rounds_left: int,
) -> dict:

    if "Prognosis" in description:
        q_table = plan_board.q_table_prognosis
        # action_table = plan_board.action_table_prognosis

    else:
        q_table = plan_board.q_table_flexrequest
        # action_table = plan_board.action_table_flexrequest

    round_now = rounds_total - rounds_left + 1

    # Use an exploration function to choose an action
    action = ta_parameter["Exploration function"](
        q_table=q_table, ta_parameter=ta_parameter, round_now=round_now
    )

    # Modify shaped markup based on choosen action function
    ta_parameter["Markup"] = ta_parameter["Action function"](
        action=action,
        markup=(
            ta_parameter["Markup"] * ta_parameter["Concession"](rounds_total=rounds_total, rounds_left=rounds_left)
        ),
        show_actions=False,
    )

    # Compute bid based on reservation price and modified markup
    ta_parameter["Bid"] = ta_parameter["Reservation price"] + ta_parameter["Markup"]

    # If TAs bid is lower than his reservation price, use reservation price instead
    if ta_parameter["Bid"] < ta_parameter["Reservation price"]:
        ta_parameter["Bid"] = ta_parameter["Reservation price"]

    # Increase exploration functions counter variable one step
    ta_parameter["Step now"] += 1

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {
        "Bid": 0,
        "Reservation price": ta_parameter["Reservation price"],
        "Markup": ta_parameter["Markup"],
        "Concession": ta_parameter["Concession"],
        "Noise": ta_parameter["Noise"],
        "Q_table": q_table,
        # "Q_Parameter": ta_parameter,
        "Action": action,
    }
