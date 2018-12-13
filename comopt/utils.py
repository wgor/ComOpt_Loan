from typing import Dict

from pandas import DataFrame, ExcelFile, isnull

from comopt.model.utils import initialize_series
from comopt.data_structures.usef_message_types import (
    Prognosis,
    FlexRequest,
    FlexOffer,
    FlexOrder,
    UdiEvent,
    DeviceMessage,
)

class Agent:
    """ Base class for a model agent. """

    def __init__(self, name: str, environment):
        """ Create a new agent. """
        self.name = name
        self.environment = environment

    def step(self):
        """ A single step of the agent. """
        pass


def data_import(file) -> Dict[str, DataFrame]:
    xl = ExcelFile(file)
    output = dict()
    for sheet in xl.sheet_names:
        if "Flags" in sheet or "EMS" in sheet:
            output[sheet] = xl.parse(sheet_name=sheet, index_col="Parameter")
        else:
            try:
                output[sheet] = xl.parse(sheet_name=sheet, index_col="time")
            except ValueError:
                output[sheet] = xl.parse(sheet_name=sheet)
    return output

def create_adverse_and_plain_offers(flex_request, best_udi_event, opportunity_costs, plan_board):

    ''' Adverse_flexoffer: Offered power and offered flexibility values comply with the requested ones.
                           commitment costs include deviation costs for each datetime where the EM-Systems plan to deviate.
        Plain_flexoffer:   Offered values and offered flexibility comply with the planned values of the EM-Systems.
                           Commitment costs include only the cost difference of the contract costs.'''

    deviation_costs_best_udi_event = initialize_series(
                                        data=None,
                                        start=flex_request.start,
                                        end=flex_request.end,
                                        resolution=flex_request.resolution)

    # If deviation costs in best_udi_event are not defined, overwrite the nan with 0 (otherwise the following calculations fail due to nan)
    for idx in best_udi_event.deviation_costs.loc[flex_request.start : (flex_request.end - flex_request.resolution)].index:
        if isnull(best_udi_event.deviation_costs.loc[idx]):
            deviation_costs_best_udi_event[idx] = 0
        else:
            deviation_costs_best_udi_event[idx] = x

    adverse_values = flex_request.requested_values.loc[
                     flex_request.start : (flex_request.end - flex_request.resolution)]

    adverse_flexibility = flex_request.requested_flexibility.loc[
                          flex_request.start : (flex_request.end - flex_request.resolution)]

    commitment_costs_best_udi_event = best_udi_event.costs + opportunity_costs

    adverse_flex_offer = FlexOffer(
                                  id=plan_board.get_message_id(),
                                  description="Adverse flex offer",
                                  offered_values=adverse_values,
                                  offered_flexibility=adverse_flexibility,
                                  deviation_cost_curve=flex_request.commitment.deviation_cost_curve,
                                  costs=commitment_costs_best_udi_event,
                                  flex_request=flex_request,
                                  )




    plain_values = best_udi_event.offered_power.loc[
                   flex_request.start : (flex_request.end - flex_request.resolution)]

    plain_flexibility = best_udi_event.offered_flexibility.loc[
                        flex_request.start : (flex_request.end - flex_request.resolution)]

    commitment_costs_best_udi_event = (best_udi_event.costs - deviation_costs_best_udi_event) + opportunity_costs

    plain_flex_offer = FlexOffer(
                                id=plan_board.get_message_id(),
                                description="Plain flex offer",
                                offered_values=plain_values,
                                offered_flexibility=plain_flexibility,
                                deviation_cost_curve=flex_request.commitment.deviation_cost_curve,
                                costs=commitment_costs_best_udi_event,
                                flex_request=flex_request,
                               )
    flex_offers = []

    if all(x == y for x,y in zip(adverse_flex_offer.offered_values, plain_flex_offer.offered_values)):
        flex_offers.append(plain_flex_offer)

    else:
        flex_offers.append(adverse_flex_offer)
        flex_offers.append(plain_flex_offer)

    return flex_offers
