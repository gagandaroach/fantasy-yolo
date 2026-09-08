"""Guards on the vendored ESPN client.

We own this code now, so its defects are ours to keep fixed — and its fixes are
ours to keep from being lost the next time upstream is merged in.
"""

from fantasy_yolo.espn.football.constant import POSITION_MAP


def test_every_slot_label_round_trips_back_to_its_id():
    """Upstream's label->id half omitted BE, IR and RB/WR/TE, so converting a
    lineup slot label back to an id returned None for exactly the slots a lineup
    write moves players between. Fixed in our copy; this keeps it fixed."""
    for slot in (0, 2, 4, 6, 16, 17, 20, 21, 23):
        label = POSITION_MAP[slot]
        assert POSITION_MAP.get(label) == slot, f"slot {slot} ({label}) does not round-trip"


def test_the_id_to_label_ordering_is_unchanged():
    """Settings.position_slot_counts slices list(POSITION_MAP.values())[:n] and
    zips it positionally against ESPN's counts. That only lands correctly while
    the int-keyed entries stay first and in slot order, so our fix appends."""
    first = list(POSITION_MAP.values())[:25]
    assert first[0] == "QB"
    assert first[20] == "BE"
    assert first[21] == "IR"
    assert first[23] == "RB/WR/TE"


def test_the_vendored_package_is_importable_under_our_namespace():
    from fantasy_yolo.espn.football import League

    assert League.__module__.startswith("fantasy_yolo.espn")


def test_nothing_imports_the_upstream_package_name():
    """A stray `from espn_api...` would silently pick up a PyPI install if the
    user happens to have one, giving two different clients in one process."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    offenders = []
    for path in (root / "src").rglob("*.py"):
        text = path.read_text()
        if "from espn_api." in text or "import espn_api\n" in text:
            offenders.append(str(path.relative_to(root)))
    assert offenders == []
