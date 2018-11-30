from datetime import datetime, timedelta

from comopt.model.environment import Environment
from comopt.scenario.balancing_opportunities import (
    single_curtailment_or_shift_each_day_between_2_and_3_am as balancing_opportunities
)
from comopt.scenario.ems_constraints import (
    limited_capacity_profile as grid_connection,
    follow_integer_test_profile,
    curtailable_integer_test_profile,
)
from comopt.scenario.ma_policies import buy_prognosis_at_random_price_between_0_and_2 as buy_prognosis_policy
from comopt.scenario.ta_policies import never_sell_prognosis as sell_prognosis_policy


def test_message_board_no_prognosis_trade():
    """Test case in which the Trading Agent never even sells a prognosis, also meaning no flex trade will occur.
    We check the message on the plan board to validate that each EMS is never consulted at all."""

    # Set up scenario
    start = datetime(year=2018, month=1, day=1, hour=6)
    end = datetime(year=2018, month=1, day=1, hour=8)
    resolution = timedelta(minutes=15)
    ems_names = ["EMS 1", "EMS 2", "EMS 3"]
    input_data = {
        "Balancing opportunities": balancing_opportunities(
            start=start, end=end, resolution=resolution
        ),
        "EMS constraints": [
            grid_connection(start=start, end=end, resolution=resolution, capacity=10),
            grid_connection(start=start, end=end, resolution=resolution, capacity=10),
            grid_connection(start=start, end=end, resolution=resolution, capacity=10),
        ],
        "Device constraints": [
            [
                follow_integer_test_profile(start=start, end=end, resolution=resolution),
                curtailable_integer_test_profile(start=start, end=end, resolution=resolution),
            ],
            [],
            [],
        ],
        "EMS prices": [(8, 10), (8, 10), (8, 10)],
        "MA Deviation Prices": (25, 25),
        "Central optimization": False,
        "MA horizon": timedelta(hours=1),
        "TA horizon": timedelta(hours=1),
        "MA prognosis policy": buy_prognosis_policy,
        "TA prognosis policy": sell_prognosis_policy,
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

    # Run simulation model
    env.run_model()

    # Assert that the TA never even communicates with any EMS, i.e. no device messages nor UDI events.
    assert [env.plan_board.message_log[ems].isnull().values.all() for ems in ems_names]
