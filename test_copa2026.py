import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone

from copa2026 import (
    build_group_tables,
    build_stage_summaries,
    current_matches,
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

    def test_render_html_shows_all_current_scoreboards(self):
        data = {
            "events": [
                event(
                    "B",
                    "Argentina",
                    "France",
                    2,
                    1,
                    completed=False,
                    date="2026-06-24T16:00Z",
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
                    date="2026-06-24T16:00Z",
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
