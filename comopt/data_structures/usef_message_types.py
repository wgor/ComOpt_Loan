from typing import Union, Optional
from pandas import Series, to_timedelta
from comopt.data_structures.message_types import (
    Prognosis as GenericPrognosis,
    Offer,
    Order,
    Request,
)

from comopt.data_structures.commitments import (
    PiecewiseConstantProfileCommitment,
    DeviationCostCurve,
)

class Prognosis(GenericPrognosis):
    """A Prognosis describes the expected power."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class FlexRequest(Request):
    """A FlexRequest describes requested commitments to deviate from a prognosis.
    A commitment for a certain timeslot of e.g. 10 MW indicates a request to increase consumption (or decrease
    production) by 10 MW.
    A nan value indicates availability to deviate by any amount."""

    def __init__(self, prognosis: Prognosis,
                requested_flexibility: Series = None,
                **kwargs):

        self.requested_flexibility = requested_flexibility
        super().__init__(**kwargs)
        self.prognosis = prognosis

        # TODO: Check if still used (does not seem so), also the values are not right. We used flex_request.commitment.constants.values instead.
        # self.requested_power = (
        #     self.prognosis.commitment.constants.loc[
        #         self.start : self.end - self.resolution
        #     ]
        #     + self.commitment.constants
        # )


class FlexOffer(Offer):
    """A FlexOffer describes offered commitments to deviate from a prognosis."""

    def __init__(
        self,
        description: str,
        flex_request: FlexRequest,
        offered_flexibility: Series = None,
        **kwargs,
    ):
        self.description = description
        self.offered_flexibility = offered_flexibility
        super().__init__(**kwargs)
        self.flex_request = flex_request
        self.prognosis = flex_request.prognosis
        # self.offered_flex = self.commitment.constants
        # self.offered_power = (
        #     self.prognosis.commitment.constants.loc[
        #         self.start : self.end - self.resolution
        #     ]
        #     + self.commitment.constants
        # )


class FlexOrder(Order):
    """A FlexOrder describes an accepted FlexOffer."""

    def __init__(self, flex_offer: FlexOffer, **kwargs):
        flex_offer.accepted = True
        self.flex_offer = flex_offer
        super().__init__(
            ordered_values=flex_offer.commitment.constants,
            deviation_cost_curve=flex_offer.commitment.deviation_cost_curve,
            costs=flex_offer.costs,
            **kwargs,
        )
        self.flex_request = flex_offer.flex_request
        self.prognosis = flex_offer.prognosis
        self.ordered_flex = self.commitment.constants
        self.ordered_power = (
            self.prognosis.commitment.constants.loc[
                self.start : self.end - self.resolution
            ]
            + self.commitment.constants
        )


class UdiEvent(Offer):
    """A UdiEvent describes a flexible energy consumption or production event."""

    # NOTE: Added offered_flexibility, contract_costs and deviation_costs as object variables.
    #       There is maybe another way to store those values, using/overwriting mother class variables (e.g. costs to total_costs).
    def __init__(
        self,
        deviation_cost_curve: DeviationCostCurve,
        contract_costs: float = None,
        deviation_costs: float = None,
        offered_flexibility: float = None,

        **kwargs,
    ):
        self.contract_costs = contract_costs
        self.deviation_costs = deviation_costs
        self.offered_flexibility = offered_flexibility
        self.deviation_cost_curve = deviation_cost_curve
        super().__init__(deviation_cost_curve=deviation_cost_curve, **kwargs)
        self.offered_power = self.commitment.constants


class DeviceMessage(Request, Order):
    """A DeviceMessage describes targeted energy consumption or production schedule.
    Can be a request or an order.
    """

    def __init__(self, type: Union[Request, Order], description: str, targeted_flexibility: Series, costs: float = None, order: bool = False, **kwargs):
        self.type = type
        self.description = description
        self.targeted_flexibility=targeted_flexibility
        if order:
            if "ordered_values" not in kwargs:
                try:
                    kwargs["ordered_values"] = kwargs["requested_values"]
                    kwargs.pop("requested_values", None)
                except KeyError:
                    raise KeyError("Specify ordered_values")
            Order.__init__(self,costs=costs, **kwargs)
            self.ordered_power = self.commitment.constants
            self.costs = costs
        else:

            Request.__init__(self, **kwargs)
            self.requested_power = self.commitment.constants
