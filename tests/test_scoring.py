from pipeline import config as C
from pipeline.features import clutch, lead_dynamics, stars
from pipeline.pbp import Event, parse
from pipeline.scoring import score


def ev(period, remaining, side, play, a, b):
    return Event(period, remaining, side, play, a, b)


def base_features(**kw):
    f = {"margin": 20, "total_points": 160, "periods": 4, "stars": [], "has_pbp": True,
         "lead_changes": 0, "ties": 0, "late_lead_changes": 0, "winner_max_deficit": 0, "clutch": None}
    f.update(kw)
    return f


# --- pbp parsing -----------------------------------------------------------

def test_parse_assigns_ot_periods_and_keeps_score():
    raw = {
        "CodeTeamA": "AAA ", "CodeTeamB": "BBB ",
        "FirstQuarter": [{"NUMBEROFPLAY": 1, "PLAYTYPE": "2FGM", "CODETEAM": "AAA", "MARKERTIME": "09:40",
                          "MINUTE": 1, "POINTS_A": 2, "POINTS_B": 0}],
        "SecondQuarter": [], "ThirdQuarter": [], "ForthQuarter": [
            {"NUMBEROFPLAY": 2, "PLAYTYPE": "3FGM", "CODETEAM": "BBB", "MARKERTIME": "00:01",
             "MINUTE": 40, "POINTS_A": 2, "POINTS_B": 3}],
        "ExtraTime": [
            {"NUMBEROFPLAY": 3, "PLAYTYPE": "FTM", "CODETEAM": "AAA", "MARKERTIME": "02:00",
             "MINUTE": 44, "POINTS_A": 3, "POINTS_B": 3},
            {"NUMBEROFPLAY": 4, "PLAYTYPE": "TO", "CODETEAM": "BBB", "MARKERTIME": "",
             "MINUTE": 44, "POINTS_A": None, "POINTS_B": None},
            {"NUMBEROFPLAY": 5, "PLAYTYPE": "2FGM", "CODETEAM": "BBB", "MARKERTIME": "04:00",
             "MINUTE": 47, "POINTS_A": 3, "POINTS_B": 5},
            {"NUMBEROFPLAY": 6, "PLAYTYPE": "EG", "CODETEAM": "", "MARKERTIME": "", "MINUTE": 51},
        ],
    }
    e = parse(raw)
    assert [x.period for x in e] == [1, 4, 5, 5, 6]
    assert e[3].remaining == 120 and (e[3].a, e[3].b) == (3, 3)  # empty clock carries over, score too
    assert [x.side for x in e] == ["A", "B", "A", "B", "B"]


# --- features --------------------------------------------------------------

def test_lead_changes_ties_late_and_deficit():
    e = [
        ev(1, 500, "A", "3FGM", 3, 0),
        ev(1, 450, "B", "3FGM", 3, 3),   # tie
        ev(1, 400, "B", "2FGM", 3, 5),   # lead change (A -> B)
        ev(3, 300, "B", "3FGM", 3, 15),  # A down 12 (via jump)
        ev(4, 100, "A", "3FGM", 16, 15),  # lead change, late
        ev(4, 50, "B", "2FGM", 16, 17),   # lead change, late
        ev(4, 10, "A", "2FGM", 18, 17),   # lead change, late
    ]
    d = lead_dynamics(e)
    assert d == {"lead_changes": 4, "ties": 1, "late_lead_changes": 3, "max_lead_a": 3, "max_lead_b": 12}


def test_clutch_kinds():
    go = [ev(4, 5, "A", "3FGM", 80, 79)]          # was 77-79, three to win
    tie = [ev(4, 3, "B", "2FGM", 80, 80)]         # was 80-78, two to tie
    miss = [ev(4, 2, "B", "3FGA", 80, 78)]        # down 2, missed three
    lead = [ev(4, 2, "A", "2FGA", 85, 78)]        # leader shooting: nothing
    early = [ev(4, 30, "A", "3FGM", 80, 79)]      # outside the window
    assert clutch(go) == "go_ahead"
    assert clutch(tie) == "tie"
    assert clutch(miss) == "missed"
    assert clutch(lead) is None
    assert clutch(early) is None
    assert clutch(miss + go) == "go_ahead"  # best moment wins


def test_stars_and_triple_double():
    box = {"Stats": [{"PlayersStats": [
        {"Player": "LLULL, SERGIO", "Team": "MAD", "Points": 31, "TotalRebounds": 2, "Assistances": 3, "Valuation": 30},
        {"Player": "X, Y", "Team": "MAD", "Points": 12, "TotalRebounds": 11, "Assistances": 10, "Valuation": 33},
        {"Player": "Z, W", "Team": "BAR", "Points": 8, "TotalRebounds": 2, "Assistances": 1, "Valuation": 5},
    ]}]}
    s = stars(box)
    assert [p["name"] for p in s] == ["Sergio Llull", "Y X"]
    assert s[1]["triple_double"] is True


# --- scoring ---------------------------------------------------------------

def test_blowout_is_skip():
    r = score(base_features(margin=30, total_points=150))
    assert r["breakdown"]["closeness"] == 0 and r["label"] == "skip"


def test_closeness_and_wire():
    r = score(base_features(margin=3))
    assert r["breakdown"]["closeness"] == min(C.CLOSENESS_CAP, (C.CLOSENESS_WINDOW - 3) * C.CLOSENESS_MULT)
    assert r["breakdown"]["wire"] == C.WIRE_BONUS
    assert any(t["k"] == "wire" for t in r["tags"])


def test_lead_changes_capped():
    r = score(base_features(lead_changes=40, ties=20))
    assert r["breakdown"]["lead_changes"] == C.LEAD_TIES_CAP


def test_overtime_late_drama_comeback_clutch():
    r = score(base_features(margin=2, periods=6, late_lead_changes=3, winner_max_deficit=14, clutch="go_ahead"))
    b = r["breakdown"]
    assert b["overtime"] == 2 * C.OT_BONUS
    assert b["late_drama"] == C.LATE_FIRST + 2 * C.LATE_EXTRA
    assert b["comeback"] == min(C.COMEBACK_CAP, (14 - C.COMEBACK_MIN + 1) * C.COMEBACK_MULT)
    assert b["clutch"] == C.CLUTCH_GO_AHEAD
    assert r["score"] == 100 and r["uncapped"] > 100 and r["label"] == "top"


def test_star_power_cap_and_flow():
    st = [{"name": "A", "pts": 41, "pir": 40, "triple_double": False, "reb": 0, "ast": 0},
          {"name": "B", "pts": 30, "pir": 10, "triple_double": False, "reb": 0, "ast": 0}]
    r = score(base_features(stars=st, total_points=200))
    assert r["breakdown"]["star_power"] == C.STAR_CAP
    assert r["breakdown"]["flow"] == C.SHOOTOUT_BONUS
    r = score(base_features(margin=15, total_points=130))
    assert r["breakdown"]["flow"] == C.GRIND_PENALTY


def test_partial_data_and_context():
    f = {"margin": 4, "total_points": 160, "periods": 4, "stars": [], "has_pbp": False}
    r = score(f, {"phase": "FF", "both_top": True})
    assert r["partial"] is True
    assert "lead_changes" not in r["breakdown"]
    assert r["breakdown"]["context"] == C.PHASE_BONUS["FF"] + C.CONTEXT_TOP_BONUS
