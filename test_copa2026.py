import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta, timezone

from copa2026 import (
    build_group_tables,
    build_stage_summaries,
    current_matches,
    dashboard_view_data,
    normalize_match,
    render_html,
    write_html_dashboard,
)


def event(
    group,
    home,
    away,
    home_score,
    away_score,
    completed=True,
    date="2026-06-11T20:00Z",
    note=None,
    home_logo="",
    away_logo="",
    state=None,
    detail=None,
):
    game_note = note if note is not None else f"FIFA World Cup, Group {group}"
    status_state = state if state is not None else ("post" if completed else "pre")
    status_detail = (
        detail if detail is not None else ("FT" if completed else "Pré-jogo")
    )
    return {
        "date": date,
        "name": f"{home} vs {away}",
        "competitions": [
            {
                "altGameNote": game_note,
                "status": {
                    "type": {
                        "completed": completed,
                        "state": status_state,
                        "shortDetail": status_detail,
                    }
                },
                "competitors": [
                    {
                        "homeAway": "home",
                        "score": str(home_score),
                        "team": {
                            "displayName": home,
                            "abbreviation": home[:3].upper(),
                            "logo": home_logo,
                        },
                    },
                    {
                        "homeAway": "away",
                        "score": str(away_score),
                        "team": {
                            "displayName": away,
                            "abbreviation": away[:3].upper(),
                            "logo": away_logo,
                        },
                    },
                ],
            }
        ],
    }


class Copa2026Tests(unittest.TestCase):
    def test_build_group_table_counts_points_and_goal_difference(self):
        events = [
            event("A", "Brasil", "Canada", 2, 0),
            event("A", "Brasil", "Mexico", 1, 1),
            event("A", "Mexico", "Canada", 3, 1),
        ]

        table = build_group_tables(events)["A"]

        self.assertEqual([team.name for team in table], ["México", "Brasil", "Canadá"])
        self.assertEqual(
            [(team.points, team.goal_difference) for team in table],
            [(4, 2), (4, 2), (0, -4)],
        )
        self.assertEqual(table[0].goals_for, 4)

    def test_build_group_table_ignores_unfinished_matches(self):
        events = [
            event("B", "Portugal", "Uzbekistan", 5, 0),
            event("B", "Portugal", "Norway", 0, 0, completed=False),
        ]

        table = build_group_tables(events)["B"]

        self.assertEqual(len(table), 2)
        self.assertEqual(table[0].name, "Portugal")
        self.assertEqual(table[0].played, 1)

    def test_normalize_match_keeps_score_and_group(self):
        match = normalize_match(
            event(
                "K",
                "Portugal",
                "Uzbekistan",
                5,
                0,
                away_logo="https://example.com/uzb.png",
            )
        )

        self.assertEqual(match["group"], "K")
        self.assertEqual(match["stage"], "Fase de grupos")
        self.assertEqual(match["home"], "Portugal")
        self.assertEqual(match["away"], "Uzbequistão")
        self.assertEqual(match["away_logo"], "https://example.com/uzb.png")
        self.assertEqual(match["away_score"], 0)
        self.assertIs(match["completed"], True)

    def test_normalize_match_detects_knockout_stage(self):
        match = normalize_match(
            event(
                None,
                "Brazil",
                "France",
                0,
                0,
                completed=False,
                note="FIFA World Cup, Round of 32",
            )
        )

        self.assertEqual(match["group"], "Sem grupo")
        self.assertEqual(match["stage"], "Fase de 32")

    def test_third_place_group_placeholder_is_not_third_place_match(self):
        fixture = event(
            None,
            "Germany",
            "Third Place Group A/B/C/D/F",
            0,
            0,
            completed=False,
            note="FIFA World Cup",
        )
        fixture["name"] = "Third Place Group A/B/C/D/F at Germany"
        fixture["shortName"] = "3RD @ GER"

        match = normalize_match(fixture)

        self.assertEqual(match["home"], "Alemanha")
        self.assertEqual(match["away"], "Third Place Group A/B/C/D/F")
        self.assertEqual(match["stage"], "Fase de 32")

    def test_winner_placeholders_are_labeled_as_next_knockout_stage(self):
        round_of_16 = event(
            None,
            "Round of 32 1 Winner",
            "Round of 32 3 Winner",
            0,
            0,
            completed=False,
            note="FIFA World Cup",
        )
        round_of_16["name"] = "Round of 32 3 Winner at Round of 32 1 Winner"
        quarterfinal = event(
            None,
            "Round of 16 1 Winner",
            "Round of 16 2 Winner",
            0,
            0,
            completed=False,
            note="FIFA World Cup",
        )
        quarterfinal["name"] = "Round of 16 2 Winner at Round of 16 1 Winner"
        final = event(
            None,
            "Semifinal 1 Winner",
            "Semifinal 2 Winner",
            0,
            0,
            completed=False,
            note="FIFA World Cup",
        )
        final["name"] = "Semifinal 2 Winner at Semifinal 1 Winner"

        self.assertEqual(normalize_match(round_of_16)["stage"], "Oitavas de final")
        self.assertEqual(normalize_match(quarterfinal)["stage"], "Quartas de final")
        self.assertEqual(normalize_match(final)["stage"], "Final")

    def test_official_round_of_32_note_keeps_group_winner_fixture_in_round_of_32(self):
        fixture = event(
            None,
            "Group H Winner",
            "Group J 2nd Place",
            0,
            0,
            completed=False,
            note="FIFA World Cup, Round of 32",
        )
        fixture["name"] = "Group J 2nd Place at Group H Winner"
        fixture["shortName"] = "2J @ 1H"

        match = normalize_match(fixture)

        self.assertEqual(match["stage"], "Fase de 32")

    def test_build_stage_summaries_counts_pending_stages_in_order(self):
        matches = [
            normalize_match(
                event(
                    "A",
                    "Brazil",
                    "Canada",
                    2,
                    0,
                    completed=True,
                    date="2026-06-11T20:00Z",
                )
            ),
            normalize_match(
                event(
                    None,
                    "Brazil",
                    "France",
                    0,
                    0,
                    completed=False,
                    date="2026-06-29T20:00Z",
                    note="FIFA World Cup, Round of 32",
                )
            ),
            normalize_match(
                event(
                    None,
                    "Argentina",
                    "Portugal",
                    0,
                    0,
                    completed=False,
                    date="2026-07-19T19:00Z",
                    note="FIFA World Cup, Final",
                )
            ),
        ]

        summaries = build_stage_summaries(
            [match for match in matches if match is not None],
            datetime(2026, 6, 24, tzinfo=timezone.utc),
        )

        self.assertEqual([summary.stage for summary in summaries], ["Fase de grupos", "Fase de 32", "Final"])
        self.assertEqual(summaries[1].total, 1)
        self.assertEqual(summaries[1].upcoming, 1)
        self.assertEqual(summaries[1].next_match["home"], "Brasil")

    def test_render_html_generates_browser_dashboard(self):
        data = {
            "events": [
                event("A", "Brazil", "Canada", 2, 0, completed=True),
                event(
                    None,
                    "Brazil",
                    "France",
                    0,
                    0,
                    completed=False,
                    date="2026-06-29T20:00Z",
                    note="FIFA World Cup, Round of 32",
                ),
            ]
        }

        content = render_html(data, "teste", None, recent_limit=5, upcoming_limit=5)

        self.assertIn("<!doctype html>", content)
        self.assertIn("Proximas etapas", content)
        self.assertIn("Fase de 32", content)
        self.assertIn("Brasil 2 x 0 Canadá", content)
        self.assertIn("Autor: Vinícius Melo Seixas", content)
        self.assertIn('url("picture_cup_2026_1.png")', content)
        self.assertIn("Placar agora", content)
        self.assertIn('aria-label="Sumario do dashboard"', content)
        self.assertIn('href="#placar-agora"', content)
        self.assertIn('id="proximas-etapas"', content)

    def test_render_html_includes_knockout_bracket(self):
        data = {
            "events": [
                event(
                    None,
                    "Brazil",
                    "France",
                    0,
                    0,
                    completed=False,
                    date="2026-06-29T20:00Z",
                    note="FIFA World Cup, Round of 32",
                ),
                event(
                    None,
                    "Semifinal 1 Winner",
                    "Semifinal 2 Winner",
                    0,
                    0,
                    completed=False,
                    date="2026-07-19T19:00Z",
                    note="FIFA World Cup",
                ),
            ]
        }
        data["events"][1]["name"] = "Semifinal 2 Winner at Semifinal 1 Winner"

        content = render_html(data, "teste", None, recent_limit=5, upcoming_limit=5)

        self.assertIn('href="#chaveamento"', content)
        self.assertIn('id="chaveamento"', content)
        self.assertIn("bracket-grid", content)
        self.assertIn("Brasil", content)
        self.assertIn("Final", content)
        self.assertIn("Campeao", content)

    def test_render_html_resolves_round_of_32_group_placeholders_from_table(self):
        data = {
            "events": [
                event("H", "Spain", "Uruguay", 2, 0),
                event("H", "Spain", "Cape Verde", 1, 0),
                event("H", "Uruguay", "Cape Verde", 3, 0),
                event(
                    None,
                    "Group H Winner",
                    "Group H 2nd Place",
                    0,
                    0,
                    completed=False,
                    date="2026-07-02T19:00Z",
                    note="FIFA World Cup, Round of 32",
                ),
            ]
        }
        data["events"][-1]["name"] = "Group H 2nd Place at Group H Winner"

        content = render_html(data, "teste", None, recent_limit=5, upcoming_limit=5)

        self.assertIn('href="#fase-32"', content)
        self.assertIn('id="fase-32"', content)
        self.assertIn("Espanha", content)
        self.assertIn("Uruguai", content)
        self.assertIn("Atual 1º Grupo H", content)
        self.assertIn("Atual 2º Grupo H", content)

    def test_render_html_translates_third_place_placeholders(self):
        data = {
            "events": [
                event("A", "Mexico", "Brazil", 2, 0),
                event("A", "Canada", "Brazil", 1, 0),
                event("A", "Mexico", "Canada", 1, 1),
                event(
                    None,
                    "Germany",
                    "Third Place Group A/B/C",
                    0,
                    0,
                    completed=False,
                    date="2026-06-29T20:00Z",
                    note="FIFA World Cup, Round of 32",
                ),
            ]
        }

        content = render_html(data, "teste", None, recent_limit=5, upcoming_limit=5)

        self.assertIn("Alemanha", content)
        self.assertIn("Melhor 3º A/B/C", content)
        self.assertIn("Candidatos: A: Brasil", content)

    def test_dashboard_does_not_duplicate_literal_team_when_slot_conflicts(self):
        data = {
            "events": [
                event(
                    None,
                    "South Africa",
                    "Canada",
                    0,
                    1,
                    date="2026-06-28T19:00Z",
                    note="FIFA World Cup, Round of 32",
                ),
                event(
                    None,
                    "Brazil",
                    "Japan",
                    2,
                    1,
                    date="2026-06-29T17:00Z",
                    note="FIFA World Cup, Round of 32",
                ),
                event(
                    None,
                    "Round of 32 2 Winner",
                    "Round of 32 5 Winner",
                    0,
                    0,
                    completed=False,
                    date="2026-07-04T21:00Z",
                    note="FIFA World Cup, Round of 16",
                ),
                event(
                    None,
                    "Brazil",
                    "Round of 32 6 Winner",
                    0,
                    0,
                    completed=False,
                    date="2026-07-05T20:00Z",
                    note="FIFA World Cup, Round of 16",
                ),
            ]
        }

        _, matches, _, _, _ = dashboard_view_data(data, None)
        round_of_16 = [
            match for match in matches if match["stage"] == "Oitavas de final"
        ]
        participants = [
            participant
            for match in round_of_16
            for participant in (match["home"], match["away"])
        ]

        self.assertEqual(participants.count("Brasil"), 1)
        self.assertEqual(round_of_16[0]["home"], "Vencedor Fase de 32 2")
        self.assertEqual(
            round_of_16[0]["home_note"],
            "A confirmar; feed também lista Brasil",
        )

    def test_render_html_shows_team_flags_when_available(self):
        data = {
            "events": [
                event(
                    "A",
                    "Brazil",
                    "Canada",
                    2,
                    0,
                    completed=True,
                    home_logo="https://example.com/bra.png",
                    away_logo="https://example.com/can.png",
                ),
            ]
        }

        content = render_html(data, "teste", None, recent_limit=5, upcoming_limit=5)

        self.assertIn('class="team-flag"', content)
        self.assertIn('src="https://example.com/bra.png"', content)
        self.assertIn('src="https://example.com/can.png"', content)

    def test_current_matches_include_live_and_started_matches(self):
        matches = [
            normalize_match(
                event(
                    "A",
                    "Brazil",
                    "Canada",
                    0,
                    0,
                    completed=False,
                    date="2026-06-24T15:00Z",
                )
            ),
            normalize_match(
                event(
                    "B",
                    "Argentina",
                    "France",
                    1,
                    0,
                    completed=False,
                    date="2026-06-24T16:00Z",
                    state="in",
                    detail="35'",
                )
            ),
        ]

        active = current_matches(
            [item for item in matches if item is not None],
            datetime(2026, 6, 24, 16, 30, tzinfo=timezone.utc),
        )

        self.assertEqual([match["home"] for match in active], ["Brasil", "Argentina"])
        self.assertEqual(active[1]["detail"], "35'")

    def test_current_matches_ignore_stale_live_cache_entries(self):
        matches = [
            normalize_match(
                event(
                    "A",
                    "Czechia",
                    "Mexico",
                    0,
                    0,
                    completed=False,
                    date="2026-06-25T01:00Z",
                    state="in",
                    detail="41'",
                )
            ),
        ]

        active = current_matches(
            [item for item in matches if item is not None],
            datetime(2026, 6, 25, 14, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(active, [])

    def test_render_html_shows_all_current_scoreboards(self):
        live_date = (
            datetime.now(timezone.utc) - timedelta(minutes=30)
        ).isoformat().replace("+00:00", "Z")
        data = {
            "events": [
                event(
                    "B",
                    "Argentina",
                    "France",
                    2,
                    1,
                    completed=False,
                    date=live_date,
                    state="in",
                    detail="70'",
                    home_logo="https://example.com/arg.png",
                    away_logo="https://example.com/fra.png",
                ),
                event(
                    "B",
                    "Switzerland",
                    "Canada",
                    0,
                    0,
                    completed=False,
                    date=live_date,
                    detail="Scheduled",
                    home_logo="https://example.com/sui.png",
                    away_logo="https://example.com/can.png",
                ),
            ]
        }

        content = render_html(data, "teste", None, recent_limit=5, upcoming_limit=5)

        self.assertIn("Placar agora", content)
        self.assertIn("Argentina 2 x 1 França", content)
        self.assertIn("Suíça 0 x 0 Canadá", content)
        self.assertIn('class="live-badge">Agora</span>', content)
        self.assertIn("70&#x27;", content)

    def test_write_html_dashboard_creates_file(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "dashboard.html"

            generated = write_html_dashboard(path, "<html></html>")

            self.assertEqual(generated, path.resolve())
            self.assertEqual(path.read_text(encoding="utf-8"), "<html></html>")

    def test_team_names_are_translated_to_portuguese(self):
        table = build_group_tables(
            [
                event("C", "Norway", "United States", 1, 2),
            ]
        )["C"]

        self.assertEqual([team.name for team in table], ["Estados Unidos", "Noruega"])


if __name__ == "__main__":
    unittest.main()
