from routing.geometry import sample_checkpoints


def test_sample_checkpoints_spacing():
    coords = [(40.0, -90.0), (40.0, -88.1)]
    cps = sample_checkpoints(coords, interval_miles=10, total_duration_seconds=7200)
    assert cps[0]["mile"] == 0.0
    assert cps[-1]["eta_offset_seconds"] == 7200
    assert len(cps) >= 2
    if len(cps) >= 3:
        assert abs((cps[1]["mile"] - cps[0]["mile"]) - 10) < 1.5
