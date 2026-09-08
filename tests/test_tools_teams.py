from fantasy_yolo.models import PlayerView
from fantasy_yolo.tools.teams import build_budget_rows, position_counts, resolve_team


class _FakeTeam:
    def __init__(self, name, team_id, spent=0, waiver_rank=1, acquisitions=0):
        self.team_name = name
        self.team_id = team_id
        self.acquisition_budget_spent = spent
        self.waiver_rank = waiver_rank
        self.acquisitions = acquisitions


def _p(position):
    return PlayerView(
        player_id=1,
        name="X",
        position=position,
        slot="BE",
        pro_team="KC",
        opponent="LV",
        projected=1.0,
        injury_status="ACTIVE",
    )


def test_position_counts_are_arithmetic_not_judgment():
    """G-03 counts. It does not say who is weak (X-01)."""
    assert position_counts([_p("RB"), _p("RB"), _p("WR")]) == {"RB": 2, "WR": 1}


def test_faab_remaining_is_budget_minus_spent():
    rows = build_budget_rows([_FakeTeam("A", 1, spent=30)], total_budget=100, faab=True)
    assert rows[0].faab_remaining == 70


def test_priority_leagues_report_waiver_rank_not_faab():
    """F-05/B-07: a bid means nothing in a rolling-priority league."""
    rows = build_budget_rows([_FakeTeam("A", 1, waiver_rank=4)], total_budget=0, faab=False)
    assert rows[0].faab_remaining is None
    assert rows[0].waiver_rank == 4


def test_budget_rows_are_ordered_by_money_available():
    teams = [_FakeTeam("Poor", 1, spent=90), _FakeTeam("Rich", 2, spent=10)]
    rows = build_budget_rows(teams, total_budget=100, faab=True)
    assert [r.team for r in rows] == ["Rich", "Poor"]


def test_resolve_team_matches_on_substring():
    teams = [_FakeTeam("The white Bhatoyas", 1), _FakeTeam("Hanuman Homies", 2)]
    assert resolve_team("bhatoyas", teams).team_id == 1


def test_resolve_team_reports_ambiguity_rather_than_guessing():
    teams = [_FakeTeam("Team One", 1), _FakeTeam("Team Two", 2)]
    try:
        resolve_team("Team", teams)
    except LookupError as exc:
        assert "Team One" in str(exc) and "Team Two" in str(exc)
    else:
        raise AssertionError("expected LookupError")


def test_all_rosters_flattens_every_team_into_owner_rows():
    """One call instead of 14. Looping the CLI per team was the workaround."""
    from fantasy_yolo.tools.teams import build_all_rosters

    rows = build_all_rosters({"A": [_p("RB"), _p("WR")], "B": [_p("QB")]})
    assert len(rows) == 3
    assert {r.team for r in rows} == {"A", "B"}


def test_all_rosters_can_be_filtered_to_positions():
    from fantasy_yolo.tools.teams import build_all_rosters

    rows = build_all_rosters({"A": [_p("RB"), _p("WR")]}, positions=["RB"])
    assert [r.player.position for r in rows] == ["RB"]


def test_position_filter_is_case_insensitive():
    from fantasy_yolo.tools.teams import build_all_rosters

    assert len(build_all_rosters({"A": [_p("RB")]}, positions=["rb"])) == 1


def test_all_rosters_of_nothing_is_empty():
    from fantasy_yolo.tools.teams import build_all_rosters

    assert build_all_rosters({}) == []
