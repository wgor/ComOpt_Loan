from typing import List, Tuple
from datetime import datetime

from comopt.data_structures.commitments import (
    PiecewiseConstantProfileCommitment as Commitment
)
from comopt.model.utils import initialize_index


def select_applicable(
    commitments: List[Commitment],
    time_window: Tuple[datetime, datetime],
    slice: bool = False,
) -> List[Commitment]:
    """Select commitments that apply to the given time window.
    If slice = True, then we cut off any commitments outside of the given time window
    and fill missing data with nan values."""

    if commitments and slice is True:
        ix = initialize_index(
            time_window[0], time_window[1], resolution=commitments[0].resolution
        )

    applicable_commitments = []
    for commitment in commitments:
        if not commitment.constants.loc[
            time_window[0] : time_window[1] - commitment.resolution
        ].empty:
            if slice is True:
                applicable_commitments.append(
                    Commitment(
                        label=commitment.label,
                        constants=commitment.constants[
                            time_window[0] : time_window[1] - commitment.resolution
                        ].reindex(ix),
                        deviation_cost_curve=commitment.deviation_cost_curve,
                    )
                )
            else:
                applicable_commitments.append(commitment)

    return applicable_commitments
