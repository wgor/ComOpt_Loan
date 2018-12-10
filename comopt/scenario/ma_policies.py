from typing import List, Optional, Union, Tuple, Callable
from random import uniform, gauss, seed
from numpy import abs, sin, cos
from comopt.model.utils import (
    root_divided_by_2,
    linear,
    cos_root_divided_by_2,
    gauss_1,
    gauss_2,
    uniform_1,
    no_noise,
)
from functools import wraps

"""Policy functions configures the strategy arguments for agents within negotiations"""

# ---------------------------------- DECORATORS ----------------------------------------#


def get_MA_bid_from_sample(policy_function: Callable):
    @wraps(policy_function)
    # @wraps allows to keep the object properties of the wrapped functions (e.g. sell_at_any_cost.__name__)
    def policy_function_wrapper(
        rounds_total: int, rounds_left: int, ma_parameter: dict
    ) -> dict:

        ma = policy_function(
            rounds_total=rounds_total,
            rounds_left=rounds_left,
            ma_parameter=ma_parameter,
        )
        ma["Markup"] = (
            ma["Markup"]
            + ma["Noise"](
                rounds_total=rounds_total, rounds_left=rounds_left, mean=ma["Markup"]
            )
        ) * ma["Concession"](rounds_total=rounds_total, rounds_left=rounds_left)

        ma["Bid"] = ma["Reservation price"] - ma["Markup"]

        # If TAs bid is lower than his reservation price, use reservation price instead
        if ma["Bid"] > ma["Reservation price"]:
            ma["Bid"] = ma["Reservation price"]

        elif ma["Bid"] < 0:
            ma["Bid"] = 0

        return {
            "Bid": ma["Bid"],
            "Reservation price": ma["Reservation price"],
            "Markup": ma["Markup"],
        }

    return policy_function_wrapper


# ---------------------------------- DECORATED POLICY FUNCTIONS ----------------------------------------#


@get_MA_bid_from_sample
# Buying with a reservation price of +inf
def never_buy(
    rounds_total: int,
    rounds_left: int,
    reservation_price=float("inf"),
    markup: Union[int, float] = 1,
    concession_curve: Union[root_divided_by_2, linear] = linear,
) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {
        "Reservation price": reservation_price,
        "Markup": markup,
        "Shape": concession_curve,
    }


@get_MA_bid_from_sample
# Selling with a reservation price of +inf
def buy_at_any_cost(
    rounds_total: int,
    rounds_left: int,
    reservation_price=float("inf"),
    markup: Union[int, float] = 1,
    concession_curve: Union[root_divided_by_2, linear] = linear,
) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {
        "Reservation price": reservation_price,
        "Markup": markup,
        "Shape": concession_curve,
    }


@get_MA_bid_from_sample
def buy_with_deterministic_prices(
    rounds_total: int, rounds_left: int, ma_parameter: dict
) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10

    return {
        "Reservation price": reservation_price,
        "Markup": markup,
        "Shape": concession_curve,
    }


@get_MA_bid_from_sample
# Samples prices from distribution
def buy_with_stochastic_prices(
    rounds_total: int, rounds_left: int, ma_parameter: dict
) -> dict:

    # Add additional logic here:
    # e.g if rounds_left == 5, then reservation_price == 10
    return {
        "Bid": 0,
        "Reservation price": ma_parameter["Reservation price"],
        "Markup": ma_parameter["Markup"],
        "Concession": ma_parameter["Concession"],
        "Noise": ma_parameter["Noise"],
    }
