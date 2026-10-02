from app.cbam_definitive_v2 import certificate_obligation


def test_certificate_obligation_applies_free_allocation_and_price():
    faa={"free_allocation_adjustment_tco2e":20.0}
    r=certificate_obligation(1.0,100,faa,75.0)
    assert r["embedded_emissions_tco2e"]==100.0
    assert r["certificates_before_carbon_price_reduction"]==80.0
    assert r["certificates_to_surrender_estimate"]==80.0
    assert r["estimated_certificate_cost_eur"]==6000.0


def test_certificate_obligation_applies_preconverted_carbon_price_reduction():
    faa={"free_allocation_adjustment_tco2e":20.0}
    r=certificate_obligation(1.0,100,faa,75.0,10.0)
    assert r["certificates_to_surrender_estimate"]==70.0
    assert r["estimated_certificate_cost_eur"]==5250.0


def test_certificate_obligation_never_goes_negative():
    faa={"free_allocation_adjustment_tco2e":120.0}
    r=certificate_obligation(1.0,100,faa,75.0,10.0)
    assert r["certificates_to_surrender_estimate"]==0.0
    assert r["estimated_certificate_cost_eur"]==0.0
