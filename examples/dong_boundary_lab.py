"""Original teaching implementation, NOT NUFER or an author-data reproduction.

Two deliberately separate boundaries:
1. A synthetic crop-livestock annual flow ledger (kg elemental N / year).
2. Dong 2026 SI S23-S49's fixed-share NH3/deposition branch, supplied with
   entirely synthetic parameters (kg elemental N / agricultural ha / year).

No network, author scripts, fitting, optimization, files or private data needed.
Run: python examples/dong_boundary_lab.py
"""
from dataclasses import asdict, dataclass
from math import isfinite
import json


def nonnegative(name, value):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name} must be numeric")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")


@dataclass(frozen=True)
class Flow:
    source: str
    target: str
    label: str
    kg_n_year: float

    def __post_init__(self):
        nonnegative(self.label, self.kg_n_year)
        if not self.source or not self.target:
            raise ValueError("A flow needs an explicit source and target")


def boundary_ledger(flows, members):
    """Count only edges that cross a specified boundary; stocks are separate sinks.

    A crop->crop recycled-straw loop is deliberately represented in gross input
    accounting, but cancels at the consolidated boundary like every internal edge.
    """
    members = set(members)
    if not members:
        raise ValueError("Boundary must have at least one member")
    gross = sum(f.kg_n_year for f in flows if f.target in members)
    internal = sum(f.kg_n_year for f in flows
                   if f.source in members and f.target in members)
    incoming = sum(f.kg_n_year for f in flows
                   if f.target in members and f.source not in members)
    outgoing = sum(f.kg_n_year for f in flows
                   if f.source in members and f.target not in members)
    return dict(gross_receipts=gross, internal_receipts=internal,
                external_receipts=incoming, external_outputs_and_stock=outgoing,
                residual=incoming-outgoing)


def synthetic_flows():
    """All 18 edge values were invented for this lesson; none are observations."""
    return [Flow(*row) for row in [
        ("outside", "crop", "chemical_fertilizer", 1200),
        ("outside", "crop", "imported_organic_fertilizer", 100),
        ("atmosphere", "crop", "deposition", 200),
        ("atmosphere", "crop", "fixation", 50),
        ("outside", "crop", "seed", 10),
        ("livestock", "crop", "recycled_manure", 300),
        ("crop", "crop", "recycled_straw", 100),
        ("crop", "livestock", "straw_feed", 150),
        ("outside", "livestock", "imported_feed", 900),
        ("crop", "food", "crop_product", 500),
        ("crop", "waste", "straw_disposal", 50),
        ("crop", "atmosphere", "crop_air_loss", 300),
        ("crop", "water", "crop_water_loss", 200),
        ("crop", "soil_stock", "crop_soil_accumulation", 660),
        ("livestock", "food", "livestock_product", 150),
        ("livestock", "byproduct", "livestock_byproduct", 50),
        ("livestock", "atmosphere", "livestock_air_loss", 200),
        ("livestock", "waste", "manure_disposal", 350),
    ]]


@dataclass(frozen=True)
class Parameters:
    # f = SI fNfe. These values are synthetic, even when a round number happens
    # to match a paper parameter. Fractions must use 0.5, NOT 50 for fifty percent.
    share_fe_fix: float = 0.75
    agricultural_land_fraction: float = 0.4
    nh3_fraction_of_deposition: float = 0.5
    nh3_ef_fe: float = 0.1
    nh3_ef_am: float = 0.2
    total_emission_ef_fe: float = 0.15
    total_emission_ef_am: float = 0.25
    surface_runoff_fraction: float = 0.05
    harvest_fraction: float = 0.6
    leaching_fraction: float = 0.7
    subsurface_runoff_fraction: float = 0.3

    def __post_init__(self):
        for name, value in asdict(self).items():
            nonnegative(name, value)
            if value > 1:
                raise ValueError(f"{name} must be a fraction between 0 and 1")
        if not 0 < self.share_fe_fix < 1:
            raise ValueError("S48-S49 implementation requires 0 < fNfe < 1")
        if self.agricultural_land_fraction == 0 or self.nh3_fraction_of_deposition == 0:
            raise ValueError("S32/S47 denominators must be positive")
        if self.nh3_ef_fe > self.total_emission_ef_fe:
            raise ValueError("Total emissions cannot be less than NH3 emissions")
        if self.nh3_ef_am > self.total_emission_ef_am:
            raise ValueError("Total emissions cannot be less than NH3 emissions")


def forward(managed_input, p=Parameters()):
    """Forward accounting from M=N_fe+fix+N_am+st, SI S23-S39.

    S25's critical-input boundary omits seed and does not separately identify
    imported organic fertilizer. This implementation does not silently map all
    S7 table categories into it. No Nmin term or disputed S51-S60 inversion used.
    """
    nonnegative("managed_input", managed_input)
    a = p.share_fe_fix * managed_input
    b = (1 - p.share_fe_fix) * managed_input
    nh3 = a*p.nh3_ef_fe + b*p.nh3_ef_am
    dep = nh3*p.agricultural_land_fraction/p.nh3_fraction_of_deposition
    total = a+b+dep
    emissions = a*p.total_emission_ef_fe + b*p.total_emission_ef_am
    sr = p.surface_runoff_fraction*managed_input
    retained = total-emissions-sr
    if retained < -1e-12:
        raise ValueError("These fractions leave negative N available after losses")
    harvest = p.harvest_fraction*retained
    surplus = retained-harvest
    leach = p.leaching_fraction*surplus
    denit = (1-p.leaching_fraction)*surplus
    subrunoff = p.subsurface_runoff_fraction*leach
    groundwater = (1-p.subsurface_runoff_fraction)*leach
    return dict(managed_input=managed_input, fe_fix=a, manure_straw=b,
                ammonia_emission=nh3, deposition=dep, total_input=total,
                total_emission=emissions, direct_runoff=sr, harvest=harvest,
                surplus=surplus, leaching=leach, denitrification=denit,
                subsurface_runoff=subrunoff, groundwater=groundwater,
                surface_water=sr+subrunoff,
                mass_balance_residual=total-emissions-sr-harvest-leach-denit)


def invert_ammonia(deposition_limit, p=Parameters()):
    """S47 -> S49 -> S48, then forward-check S25/S28/S32.

    deposition_limit is kg elemental N / natural-land ha / year. S40-S47 assume
    equal areal deposition on agricultural and natural land. Output ammonia is
    kg elemental N / agricultural ha / year, NOT kg NH3 compound mass.
    """
    nonnegative("deposition_limit", deposition_limit)
    nh3_limit = (deposition_limit*p.nh3_fraction_of_deposition /
                 p.agricultural_land_fraction)
    ratio = p.share_fe_fix/(1-p.share_fe_fix)
    denominator = p.nh3_ef_am + p.nh3_ef_fe*ratio
    if denominator <= 0:
        raise ValueError("No finite NH3-based upper bound when both emission factors are zero")
    b = nh3_limit/denominator
    a = ratio*b
    return forward(a+b, p)


def conditional_interval(target_harvest, deposition_limit, p=Parameters()):
    """Self-derived teaching target, NOT paper Eq.10 or S5 yield reproduction.

    For fixed coefficients S26 is linear in M. Invert that relation for a
    synthetic harvest-N target; intersect with this single NH3 boundary.
    Water quality, P, economic or agronomic feasibility are NOT certified.
    """
    nonnegative("target_harvest", target_harvest)
    unit = forward(1.0, p)
    if unit["harvest"] <= 0:
        raise ValueError("A positive harvest response is needed for this inversion")
    lower = forward(target_harvest/unit["harvest"], p)
    upper = invert_ammonia(deposition_limit, p)
    return dict(target_harvest=target_harvest,
                managed_input_lower=lower["managed_input"],
                managed_input_upper=upper["managed_input"],
                total_input_lower=lower["total_input"],
                total_input_upper=upper["total_input"],
                nonempty=lower["managed_input"] <= upper["managed_input"]+1e-10)


def printed_table_audit():
    """Independent arithmetic on S6/S7's printed values, not a model rerun."""
    crop_components = [187.2, 42.2, 3.2, 0.4, 38.2, 6.9, 36.0]
    livestock_components = [164.6, 5.2]
    crop = sum(crop_components)
    livestock = sum(livestock_components)
    net = crop + livestock - 36.0 - 6.9 - 5.2
    return dict(
        source="Dong 2026 SI render p30 Table S6; pp31-32 Table S7",
        source_value_kind="printed source table values, not synthetic and not raw author data",
        crop_input_component_sum=crop, crop_input_printed_sum=314,
        livestock_input_component_sum=livestock, livestock_input_printed_sum=170,
        consolidated_input_component_sum=net, consolidated_input_printed_sum=436,
        crop_less_deposition_and_fixation=crop-42.2-3.2,
        s6_anthropogenic_printed=268,
        unexplained_difference=(crop-42.2-3.2)-268,
        exceedance_percent={
            "source_EU_label_anthropogenic": (268/262-1)*100,
            "groundwater_total_input": (314/218-1)*100,
            "ammonia_total_input": (314/187-1)*100,
            "surface_water_total_input": (314/174-1)*100},
        caution="268.7 vs 268 is not resolved by merely naming the boundary; do not silently correct the source.")


def demonstration():
    flows = synthetic_flows()
    crop = boundary_ledger(flows, {"crop"})
    livestock = boundary_ledger(flows, {"livestock"})
    combined = boundary_ledger(flows, {"crop", "livestock"})
    return dict(
        disclaimer="Original synthetic teaching calculation; no author code, fitting or full NUFER reproduction",
        synthetic_flow_unit="kg elemental N / year",
        synthetic_flows=[asdict(f) for f in flows],
        synthetic_ledger={"crop": crop, "livestock": livestock, "combined": combined,
                          "crop_nue_gross_definition": (500+100+150+50)/crop["gross_receipts"],
                          "livestock_nue": (150+50)/livestock["gross_receipts"],
                          "combined_nue": (500+150+50)/combined["external_receipts"]},
        synthetic_parameters=asdict(Parameters()),
        synthetic_boundary_unit="kg elemental N / agricultural ha / year",
        synthetic_deposition_limit=10,
        synthetic_ammonia_upper=invert_ammonia(10),
        synthetic_target_50=conditional_interval(50,10),
        synthetic_target_55=conditional_interval(55,10),
        printed_source_audit=printed_table_audit())


if __name__ == "__main__":
    print(json.dumps(demonstration(), ensure_ascii=False, indent=2))
