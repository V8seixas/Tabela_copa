#!/usr/bin/env python3
"""Acompanha placares e tabela da Copa do Mundo FIFA 2026."""

from __future__ import annotations

import argparse
import html
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
)
TOURNAMENT_START = date(2026, 6, 11)
TOURNAMENT_END = date(2026, 7, 19)
DEFAULT_CACHE = Path(".cache/copa2026-scoreboard.json")
AUTHOR = "Vinícius Melo Seixas"
DASHBOARD_BACKGROUND_IMAGE = "picture_cup_2026_1.png"
CURRENT_MATCH_WINDOW = timedelta(hours=3)
TEAM_NAME_TRANSLATIONS = {
    "Albania": "Albânia",
    "Algeria": "Argélia",
    "Angola": "Angola",
    "Argentina": "Argentina",
    "Australia": "Austrália",
    "Austria": "Áustria",
    "Belgium": "Bélgica",
    "Bolivia": "Bolívia",
    "Bosnia and Herzegovina": "Bósnia e Herzegovina",
    "Bosnia-Herzegovina": "Bósnia e Herzegovina",
    "Brazil": "Brasil",
    "Bulgaria": "Bulgária",
    "Burkina Faso": "Burkina Faso",
    "Cameroon": "Camarões",
    "Canada": "Canadá",
    "Cape Verde": "Cabo Verde",
    "Chile": "Chile",
    "China": "China",
    "Colombia": "Colômbia",
    "Costa Rica": "Costa Rica",
    "Croatia": "Croácia",
    "Czechia": "Tchéquia",
    "Czech Republic": "República Tcheca",
    "Denmark": "Dinamarca",
    "Ecuador": "Equador",
    "Egypt": "Egito",
    "El Salvador": "El Salvador",
    "England": "Inglaterra",
    "France": "França",
    "Germany": "Alemanha",
    "Ghana": "Gana",
    "Greece": "Grécia",
    "Guatemala": "Guatemala",
    "Haiti": "Haiti",
    "Honduras": "Honduras",
    "Hungary": "Hungria",
    "Iceland": "Islândia",
    "Indonesia": "Indonésia",
    "Iran": "Irã",
    "Iraq": "Iraque",
    "Ireland": "Irlanda",
    "Israel": "Israel",
    "Italy": "Itália",
    "Ivory Coast": "Costa do Marfim",
    "Jamaica": "Jamaica",
    "Japan": "Japão",
    "Jordan": "Jordânia",
    "Korea Republic": "Coreia do Sul",
    "Kosovo": "Kosovo",
    "Mali": "Mali",
    "Mexico": "México",
    "Morocco": "Marrocos",
    "Netherlands": "Países Baixos",
    "New Zealand": "Nova Zelândia",
    "Nigeria": "Nigéria",
    "North Macedonia": "Macedônia do Norte",
    "Northern Ireland": "Irlanda do Norte",
    "Norway": "Noruega",
    "Panama": "Panamá",
    "Paraguay": "Paraguai",
    "Peru": "Peru",
    "Poland": "Polônia",
    "Portugal": "Portugal",
    "Qatar": "Catar",
    "Romania": "Romênia",
    "Russia": "Rússia",
    "Saudi Arabia": "Arábia Saudita",
    "Scotland": "Escócia",
    "Senegal": "Senegal",
    "Serbia": "Sérvia",
    "Slovakia": "Eslováquia",
    "Slovenia": "Eslovênia",
    "South Africa": "África do Sul",
    "Spain": "Espanha",
    "Sweden": "Suécia",
    "Switzerland": "Suíça",
    "Tunisia": "Tunísia",
    "Turkey": "Turquia",
    "Ukraine": "Ucrânia",
    "United Arab Emirates": "Emirados Árabes Unidos",
    "United States": "Estados Unidos",
    "Uruguay": "Uruguai",
    "Uzbekistan": "Uzbequistão",
    "Venezuela": "Venezuela",
    "Wales": "País de Gales",
}
STAGE_ORDER = {
    "Fase de grupos": 0,
    "Fase de 32": 1,
    "Oitavas de final": 2,
    "Quartas de final": 3,
    "Semifinais": 4,
    "Disputa de 3o lugar": 5,
    "Final": 6,
    "Mata-mata": 7,
}
KNOCKOUT_BRACKET_STAGES = (
    "Fase de 32",
    "Oitavas de final",
    "Quartas de final",
    "Semifinais",
    "Final",
)


@dataclass
class TeamStats:
    group: str
    name: str
    abbreviation: str
    logo: str = ""
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    def record_result(self, goals_for: int, goals_against: int) -> None:
        self.played += 1
        self.goals_for += goals_for
        self.goals_against += goals_against

        if goals_for > goals_against:
            self.wins += 1
            self.points += 3
        elif goals_for == goals_against:
            self.draws += 1
            self.points += 1
        else:
            self.losses += 1


@dataclass
class StageSummary:
    stage: str
    total: int = 0
    completed: int = 0
    upcoming: int = 0
    first_date: datetime | None = None
    last_date: datetime | None = None
    next_match: dict[str, Any] | None = None

    @property
    def pending(self) -> int:
        return self.total - self.completed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mostra resultados recentes e tabela da Copa do Mundo 2026."
    )
    parser.add_argument(
        "--data",
        default=TOURNAMENT_END.isoformat(),
        help="data final da consulta no formato AAAA-MM-DD (padrao: fim da Copa)",
    )
    parser.add_argument(
        "--inicio",
        default=TOURNAMENT_START.isoformat(),
        help="data inicial da consulta no formato AAAA-MM-DD",
    )
    parser.add_argument(
        "--grupo",
        help="mostra apenas um grupo, por exemplo A, B ou K",
    )
    parser.add_argument(
        "--proximos",
        type=int,
        default=8,
        help="quantidade de proximos jogos para mostrar",
    )
    parser.add_argument(
        "--recentes",
        type=int,
        default=8,
        help="quantidade de resultados recentes para mostrar",
    )
    parser.add_argument(
        "--cache",
        default=str(DEFAULT_CACHE),
        help="arquivo de cache usado quando a internet falhar",
    )
    parser.add_argument(
        "--sem-cache",
        action="store_true",
        help="nao usa dados antigos se a consulta online falhar",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="imprime os dados normalizados em JSON",
    )
    parser.add_argument(
        "--html",
        metavar="ARQUIVO",
        help="gera um dashboard HTML no arquivo informado, por exemplo dashboard.html",
    )
    parser.add_argument(
        "--watch",
        type=int,
        metavar="SEGUNDOS",
        help="atualiza a tela automaticamente no intervalo informado",
    )
    return parser.parse_args()


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Data invalida: {value}. Use AAAA-MM-DD.") from exc


def fetch_scoreboard(start: date, end: date, timeout: int = 20) -> dict[str, Any]:
    if end < start:
        raise SystemExit("A data final nao pode ser anterior a data inicial.")

    params = urllib.parse.urlencode(
        {
            "dates": f"{start:%Y%m%d}-{end:%Y%m%d}",
            "limit": "200",
        }
    )
    request = urllib.request.Request(
        f"{ESPN_SCOREBOARD_URL}?{params}",
        headers={
            "Accept": "application/json",
            "User-Agent": "copa2026-python/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def read_cache(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_scoreboard(
    start: date, end: date, cache_path: Path, allow_cache: bool
) -> tuple[dict[str, Any], str]:
    try:
        data = fetch_scoreboard(start, end)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        if allow_cache and cache_path.exists():
            return (
                read_cache(cache_path),
                f"cache ({cache_path}) por falha online: {exc}",
            )
        raise SystemExit(f"Falha ao buscar dados online: {exc}") from exc

    write_cache(cache_path, data)
    return data, "online"


def event_competition(event: dict[str, Any]) -> dict[str, Any]:
    competitions = event.get("competitions") or []
    return competitions[0] if competitions else {}


def competition_teams(
    competition: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    competitors = competition.get("competitors") or []
    if len(competitors) < 2:
        raise ValueError("competicao sem dois times")

    home = next(
        (item for item in competitors if item.get("homeAway") == "home"),
        competitors[0],
    )
    away = next(
        (item for item in competitors if item.get("homeAway") == "away"),
        competitors[1],
    )
    return home, away


def group_name(competition: dict[str, Any]) -> str:
    note = competition.get("altGameNote") or ""
    if "Group " in note:
        return note.rsplit("Group ", maxsplit=1)[-1].strip()
    return "Sem grupo"


def stage_name(event: dict[str, Any], competition: dict[str, Any]) -> str:
    if is_group_stage(competition):
        return "Fase de grupos"

    values = [
        competition.get("altGameNote"),
        competition.get("note"),
        event.get("name"),
        event.get("shortName"),
    ]
    text = " ".join(str(value) for value in values if value).lower()

    if any(term in text for term in ("third place group", "third-place group")):
        return "Fase de 32"
    if "semifinal" in text and "loser" in text:
        return "Disputa de 3o lugar"
    if "semifinal" in text and "winner" in text:
        return "Final"
    if "quarterfinal" in text and "winner" in text:
        return "Semifinais"
    if "round of 16" in text and "winner" in text:
        return "Quartas de final"
    if "round of 32" in text and "winner" in text:
        return "Oitavas de final"
    if any(term in text for term in ("third-place", "third place", "3rd place")):
        return "Disputa de 3o lugar"
    if any(term in text for term in ("semifinal", "semi-final", "semifinais")):
        return "Semifinais"
    if any(term in text for term in ("quarterfinal", "quarter-final", "quartas")):
        return "Quartas de final"
    if any(term in text for term in ("round of 16", "oitavas")):
        return "Oitavas de final"
    if any(term in text for term in ("round of 32", "fase de 32")):
        return "Fase de 32"
    if "final" in text:
        return "Final"
    return "Fase de 32"


def is_completed(competition: dict[str, Any]) -> bool:
    return bool(competition.get("status", {}).get("type", {}).get("completed"))


def is_group_stage(competition: dict[str, Any]) -> bool:
    return group_name(competition) != "Sem grupo"


def team_identity(competitor: dict[str, Any]) -> tuple[str, str, str]:
    team = competitor.get("team") or {}
    name = team.get("displayName") or team.get("name") or "Desconhecido"
    abbreviation = team.get("abbreviation") or name[:3].upper()
    logo = team.get("logo") or ""
    return translate_team_name(name), abbreviation, logo


def translate_team_name(name: str) -> str:
    return TEAM_NAME_TRANSLATIONS.get(name.strip(), name)


def score(competitor: dict[str, Any]) -> int:
    value = competitor.get("score")
    if value in (None, ""):
        return 0
    return int(value)


def build_group_tables(events: list[dict[str, Any]]) -> dict[str, list[TeamStats]]:
    tables: dict[str, dict[str, TeamStats]] = {}

    for event in events:
        competition = event_competition(event)
        if (
            not competition
            or not is_completed(competition)
            or not is_group_stage(competition)
        ):
            continue

        try:
            home, away = competition_teams(competition)
        except ValueError:
            continue

        group = group_name(competition)
        tables.setdefault(group, {})
        home_name, home_abbr, home_logo = team_identity(home)
        away_name, away_abbr, away_logo = team_identity(away)

        tables[group].setdefault(
            group_key(group, home_name),
            TeamStats(group, home_name, home_abbr, home_logo),
        )
        tables[group].setdefault(
            group_key(group, away_name),
            TeamStats(group, away_name, away_abbr, away_logo),
        )

        home_score = score(home)
        away_score = score(away)
        tables[group][group_key(group, home_name)].record_result(home_score, away_score)
        tables[group][group_key(group, away_name)].record_result(away_score, home_score)

    return {
        group: sorted(stats.values(), key=team_sort_key)
        for group, stats in sorted(tables.items(), key=lambda item: item[0])
    }


def group_key(group: str, team_name: str) -> str:
    return f"{group}:{team_name}"


def team_sort_key(team: TeamStats) -> tuple[int, int, int, str]:
    return (-team.points, -team.goal_difference, -team.goals_for, team.name)


def event_datetime(event: dict[str, Any]) -> datetime:
    raw = event.get("date") or event_competition(event).get("date")
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def normalize_match(event: dict[str, Any]) -> dict[str, Any] | None:
    competition = event_competition(event)
    if not competition:
        return None

    try:
        home, away = competition_teams(competition)
    except ValueError:
        return None

    home_name, home_abbr, home_logo = team_identity(home)
    away_name, away_abbr, away_logo = team_identity(away)
    status = competition.get("status", {}).get("type", {})

    return {
        "date": event_datetime(event).isoformat(),
        "group": group_name(competition),
        "stage": stage_name(event, competition),
        "venue": (competition.get("venue") or {}).get("fullName", ""),
        "home": home_name,
        "home_abbr": home_abbr,
        "home_logo": home_logo,
        "away": away_name,
        "away_abbr": away_abbr,
        "away_logo": away_logo,
        "home_score": score(home),
        "away_score": score(away),
        "completed": bool(status.get("completed")),
        "state": status.get("state", ""),
        "detail": status.get("shortDetail")
        or status.get("detail")
        or status.get("description", ""),
    }


def normalized_payload(
    events: list[dict[str, Any]], tables: dict[str, list[TeamStats]]
) -> dict[str, Any]:
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": ESPN_SCOREBOARD_URL,
        "tables": {
            group: [
                team.__dict__ | {"goal_difference": team.goal_difference}
                for team in teams
            ]
            for group, teams in tables.items()
        },
        "matches": [
            match
            for match in (normalize_match(event) for event in events)
            if match is not None
        ],
    }


def build_stage_summaries(
    matches: list[dict[str, Any]], now: datetime | None = None
) -> list[StageSummary]:
    reference = now or datetime.now(timezone.utc)
    summaries: dict[str, StageSummary] = {}

    for match in matches:
        stage = str(match.get("stage") or "Mata-mata")
        summary = summaries.setdefault(stage, StageSummary(stage))
        match_date = datetime.fromisoformat(match["date"])

        summary.total += 1
        if match["completed"]:
            summary.completed += 1
        elif match_date >= reference:
            summary.upcoming += 1
            if summary.next_match is None or match_date < datetime.fromisoformat(
                summary.next_match["date"]
            ):
                summary.next_match = match

        if summary.first_date is None or match_date < summary.first_date:
            summary.first_date = match_date
        if summary.last_date is None or match_date > summary.last_date:
            summary.last_date = match_date

    return sorted(
        summaries.values(),
        key=lambda item: (
            STAGE_ORDER.get(item.stage, len(STAGE_ORDER)),
            item.first_date or datetime.max.replace(tzinfo=timezone.utc),
            item.stage,
        ),
    )


def render(
    data: dict[str, Any],
    source_label: str,
    selected_group: str | None,
    recent_limit: int,
    upcoming_limit: int,
) -> str:
    events = sorted(data.get("events", []), key=event_datetime)
    tables = build_group_tables(events)
    matches = [
        match
        for match in (normalize_match(event) for event in events)
        if match is not None
    ]
    if selected_group:
        group_filter = selected_group.upper()
        matches = [
            match for match in matches if str(match["group"]).upper() == group_filter
        ]
    now = datetime.now(timezone.utc)
    completed = [match for match in matches if match["completed"]]
    upcoming = [
        match
        for match in matches
        if not match["completed"] and datetime.fromisoformat(match["date"]) >= now
    ]
    stage_summaries = build_stage_summaries(matches, now)

    lines = dashboard_header(source_label, selected_group)
    append_dashboard_summary(
        lines, matches, tables, completed, upcoming, selected_group
    )
    append_stage_dashboard(lines, stage_summaries)
    append_tables(lines, tables, selected_group)
    append_upcoming(lines, upcoming[:upcoming_limit] if upcoming_limit else [])
    append_recent_results(lines, completed[-recent_limit:] if recent_limit else [])
    return "\n".join(lines).rstrip() + "\n"


def dashboard_view_data(
    data: dict[str, Any],
    selected_group: str | None,
) -> tuple[
    dict[str, list[TeamStats]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[StageSummary],
]:
    events = sorted(data.get("events", []), key=event_datetime)
    tables = build_group_tables(events)
    matches = [
        match
        for match in (normalize_match(event) for event in events)
        if match is not None
    ]
    if selected_group:
        group_filter = selected_group.upper()
        matches = [
            match for match in matches if str(match["group"]).upper() == group_filter
        ]

    now = datetime.now(timezone.utc)
    completed = [match for match in matches if match["completed"]]
    upcoming = [
        match
        for match in matches
        if not match["completed"] and datetime.fromisoformat(match["date"]) >= now
    ]
    stage_summaries = build_stage_summaries(matches, now)
    return tables, matches, completed, upcoming, stage_summaries


def live_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        match
        for match in matches
        if not match["completed"] and str(match.get("state", "")).lower() == "in"
    ]


def current_matches(
    matches: list[dict[str, Any]], now: datetime | None = None
) -> list[dict[str, Any]]:
    reference = now or datetime.now(timezone.utc)
    active = [match for match in matches if is_current_match(match, reference)]
    return sorted(
        active,
        key=lambda match: (
            datetime.fromisoformat(match["date"]),
            str(match.get("home") or ""),
            str(match.get("away") or ""),
        ),
    )


def is_current_match(match: dict[str, Any], reference: datetime) -> bool:
    if match["completed"]:
        return False

    match_date = datetime.fromisoformat(match["date"])
    if match_date > reference:
        return False
    if reference - match_date > CURRENT_MATCH_WINDOW:
        return False

    state = str(match.get("state", "")).lower()
    return state == "in" or match_date <= reference


def current_match(
    matches: list[dict[str, Any]], now: datetime | None = None
) -> dict[str, Any] | None:
    active = current_matches(matches, now)
    return active[0] if active else None


def render_html(
    data: dict[str, Any],
    source_label: str,
    selected_group: str | None,
    recent_limit: int,
    upcoming_limit: int,
) -> str:
    tables, matches, completed, upcoming, stage_summaries = dashboard_view_data(
        data,
        selected_group,
    )
    selected = selected_group.upper() if selected_group else None
    visible_tables = {
        group: teams
        for group, teams in tables.items()
        if selected in (None, group.upper())
    }
    leader = best_campaign(visible_tables)
    leader_label = (
        f"{leader.name} ({leader.points} pts)" if leader is not None else "Sem dados"
    )
    live_matches_now = current_matches(matches)
    updated = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    group_label = selected_group.upper() if selected_group else "Todos"

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tabela da Copa do Mundo 2026</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: rgba(255, 255, 255, 0.80);
      --text: #1b2430;
      --muted: #667085;
      --line: #d8dee9;
      --accent: #0969da;
      --accent-soft: #e7f0ff;
      --green: #147a3f;
      --gold: #9a6700;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(rgba(5, 10, 24, 0.58), rgba(5, 10, 24, 0.72)),
        url("{escape_html(DASHBOARD_BACKGROUND_IMAGE)}") center top / cover fixed no-repeat,
        var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.4;
    }}
    header {{
      background: rgba(15, 23, 42, 0.88);
      color: #ffffff;
      padding: 24px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.18);
    }}
    main {{
      width: min(1180px, calc(100% - 32px));
      margin: 24px auto 40px;
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{ margin-bottom: 8px; font-size: 28px; }}
    h2, h3 {{
      color: #ffffff;
      text-shadow: 0 1px 3px rgba(0, 0, 0, 0.55);
    }}
    h2 {{ margin: 28px 0 12px; font-size: 22px; }}
    h3 {{ margin: 18px 0 10px; font-size: 18px; }}
    .meta {{ color: #d7dce6; margin: 0; }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    .toc {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.16);
    }}
    .toc h2 {{
      margin: 0 0 12px;
      color: var(--text);
      text-shadow: none;
    }}
    .toc-links {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
    }}
    .toc-links a {{
      display: flex;
      align-items: center;
      min-height: 42px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }}
    .toc-links a:hover {{
      background: var(--accent-soft);
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.16);
    }}
    .card span {{
      display: block;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .card strong {{ font-size: 22px; }}
    .table-wrap {{
      overflow-x: auto;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.16);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 720px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      white-space: nowrap;
    }}
    th {{
      background: #eef2f7;
      color: #344054;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .02em;
    }}
    tr:last-child td {{ border-bottom: 0; }}
    .team {{ font-weight: 700; }}
    .team-label {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}
    .team-flag {{
      width: 22px;
      height: 22px;
      object-fit: contain;
      flex: 0 0 22px;
      border: 1px solid var(--line);
      border-radius: 50%;
      background: #fff;
    }}
    .stage {{ color: var(--accent); font-weight: 700; }}
    .status-ok {{ color: var(--green); font-weight: 700; }}
    .status-next {{ color: var(--gold); font-weight: 700; }}
    .matches {{
      display: grid;
      gap: 10px;
    }}
    .match {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.16);
    }}
    .match-top {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .score {{
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 6px;
      font-size: 17px;
      font-weight: 700;
    }}
    .live-scoreboard {{
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid rgba(9, 105, 218, 0.32);
      border-left: 6px solid var(--accent);
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 16px 34px rgba(15, 23, 42, 0.22);
    }}
    .live-scoreboards {{
      display: grid;
      gap: 12px;
    }}
    .live-meta {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px 14px;
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 14px;
    }}
    .live-badge {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 10px;
      border-radius: 999px;
      background: #d92d20;
      color: #ffffff;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .live-teams {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
      align-items: center;
      gap: 14px;
    }}
    .live-team {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      min-width: 0;
    }}
    .live-team .team-label {{
      min-width: 0;
      font-size: 20px;
      font-weight: 700;
    }}
    .live-team strong {{
      flex: 0 0 auto;
      min-width: 44px;
      text-align: center;
      font-size: 34px;
      line-height: 1;
      color: var(--accent);
    }}
    .live-versus {{
      color: var(--muted);
      font-size: 18px;
      font-weight: 700;
    }}
    .live-detail {{
      margin-top: 12px;
      color: var(--muted);
      font-weight: 700;
    }}
    .empty {{
      background: var(--panel);
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 16px;
      color: var(--muted);
    }}
{html_knockout_bracket_styles()}
    @media (max-width: 700px) {{
      .live-teams {{
        grid-template-columns: 1fr;
        gap: 10px;
      }}
      .live-versus {{
        display: none;
      }}
      .live-team {{
        padding: 10px 0;
        border-top: 1px solid var(--line);
      }}
      .live-team:first-child {{
        border-top: 0;
      }}
    }}
    footer {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto 28px;
      color: rgba(255, 255, 255, 0.82);
      font-size: 13px;
      text-shadow: 0 1px 3px rgba(0, 0, 0, 0.55);
    }}
  </style>
</head>
<body>
  <header>
    <h1>Copa do Mundo 2026 - Dashboard</h1>
    <p class="meta">Atualizado: {escape_html(updated)} | Fonte: {escape_html(source_label)} | Grupo: {escape_html(group_label)}</p>
    <p class="meta">Autor: {escape_html(AUTHOR)}</p>
  </header>
  <main>
    {html_summary_cards(matches, completed, upcoming, leader_label)}
    {html_dashboard_toc()}
    {html_live_scoreboard(live_matches_now)}
    {html_stage_dashboard(stage_summaries)}
    {html_knockout_bracket(matches)}
    {html_group_tables(visible_tables)}
    {html_match_section("Proximos jogos", upcoming[:upcoming_limit] if upcoming_limit else [], include_score=False)}
    {html_match_section("Resultados recentes", completed[-recent_limit:] if recent_limit else [], include_score=True)}
  </main>
  <footer>Autor: {escape_html(AUTHOR)}</footer>
</body>
</html>
"""


def html_knockout_bracket_styles() -> str:
    return """
    .knockout-bracket {
      margin-top: 28px;
      padding: 18px;
      overflow: hidden;
      background: rgba(7, 17, 35, 0.92);
      border: 1px solid rgba(125, 211, 252, 0.36);
      border-radius: 8px;
      box-shadow: 0 18px 42px rgba(3, 10, 28, 0.34);
    }
    .knockout-bracket h2 {
      margin-bottom: 6px;
    }
    .bracket-note {
      margin: 0 0 16px;
      color: #cbd5e1;
      font-size: 13px;
    }
    .bracket-scroll {
      overflow-x: auto;
      padding: 4px 2px 10px;
    }
    .bracket-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(178px, 1fr)) minmax(220px, 1.1fr) repeat(4, minmax(178px, 1fr));
      gap: 14px;
      min-width: 1680px;
      align-items: center;
    }
    .bracket-round {
      display: grid;
      align-content: center;
      gap: 10px;
      min-height: 100%;
    }
    .bracket-round-title {
      min-height: 28px;
      color: #bae6fd;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: .04em;
      text-align: center;
      text-transform: uppercase;
    }
    .bracket-match {
      position: relative;
      display: grid;
      gap: 8px;
      min-height: 118px;
      padding: 10px;
      background: rgba(15, 23, 42, 0.90);
      border: 1px solid rgba(96, 165, 250, 0.38);
      border-radius: 8px;
      color: #f8fafc;
      box-shadow: 0 0 18px rgba(37, 99, 235, 0.16);
    }
    .bracket-round.left .bracket-match::after,
    .bracket-final-card::before,
    .bracket-round.right .bracket-match::before {
      content: "";
      position: absolute;
      top: 50%;
      width: 14px;
      border-top: 1px solid rgba(125, 211, 252, 0.48);
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.28);
    }
    .bracket-round.left .bracket-match::after {
      right: -15px;
    }
    .bracket-round.right .bracket-match::before {
      left: -15px;
    }
    .bracket-final-card::before {
      left: -15px;
    }
    .bracket-final-card::after {
      content: "";
      position: absolute;
      top: 50%;
      right: -15px;
      width: 14px;
      border-top: 1px solid rgba(125, 211, 252, 0.48);
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.28);
    }
    .bracket-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 6px 10px;
      color: #cbd5e1;
      font-size: 11px;
      font-weight: 700;
    }
    .bracket-team {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: center;
      gap: 8px;
      min-height: 28px;
      padding: 5px 0;
      border-top: 1px solid rgba(148, 163, 184, 0.20);
    }
    .bracket-team:first-of-type {
      border-top: 0;
    }
    .bracket-team .team-label {
      min-width: 0;
      color: #f8fafc;
      font-size: 13px;
      font-weight: 800;
    }
    .bracket-team .team-label img {
      flex: 0 0 20px;
    }
    .bracket-team.winner .team-label,
    .bracket-team.winner .bracket-score {
      color: #86efac;
    }
    .bracket-score {
      min-width: 28px;
      color: #dbeafe;
      font-weight: 900;
      text-align: right;
    }
    .bracket-status {
      color: #93c5fd;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
    }
    .bracket-placeholder {
      display: grid;
      min-height: 92px;
      place-items: center;
      padding: 12px;
      color: #94a3b8;
      border: 1px dashed rgba(148, 163, 184, 0.38);
      border-radius: 8px;
      background: rgba(15, 23, 42, 0.44);
      font-size: 13px;
      font-weight: 700;
      text-align: center;
    }
    .bracket-center {
      display: grid;
      gap: 12px;
      align-content: center;
    }
    .bracket-final-card,
    .bracket-champion {
      position: relative;
      border-radius: 8px;
    }
    .bracket-final-card {
      border: 1px solid rgba(250, 204, 21, 0.54);
      box-shadow: 0 0 22px rgba(250, 204, 21, 0.14);
    }
    .bracket-champion {
      display: grid;
      min-height: 112px;
      place-items: center;
      padding: 14px;
      background: linear-gradient(180deg, rgba(30, 41, 59, 0.96), rgba(88, 62, 9, 0.70));
      border: 1px solid rgba(250, 204, 21, 0.62);
      color: #fef3c7;
      text-align: center;
      box-shadow: 0 0 26px rgba(250, 204, 21, 0.16);
    }
    .bracket-champion span {
      display: block;
      color: #fde68a;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: .05em;
      text-transform: uppercase;
    }
    .bracket-champion strong {
      display: block;
      margin-top: 8px;
      font-size: 20px;
      line-height: 1.15;
    }
    @media (max-width: 700px) {
      .knockout-bracket {
        padding: 14px;
      }
      .bracket-grid {
        min-width: 1540px;
        grid-template-columns: repeat(4, 164px) 204px repeat(4, 164px);
        gap: 10px;
      }
    }"""


def html_knockout_bracket(matches: list[dict[str, Any]]) -> str:
    rounds = knockout_bracket_rounds(matches)
    if not any(rounds.values()):
        return """    <section id="chaveamento" class="knockout-bracket">
      <h2>Chaveamento</h2>
      <p class="empty">Nenhum jogo de mata-mata encontrado no periodo consultado.</p>
    </section>"""

    side_stages = KNOCKOUT_BRACKET_STAGES[:-1]
    split_rounds = {
        stage: split_bracket_matches(rounds.get(stage, [])) for stage in side_stages
    }
    left_rounds = "\n".join(
        html_bracket_round(stage, split_rounds[stage][0], "left")
        for stage in side_stages
    )
    right_rounds = "\n".join(
        html_bracket_round(stage, split_rounds[stage][1], "right")
        for stage in reversed(side_stages)
    )
    final_match = rounds["Final"][0] if rounds["Final"] else None

    return f"""    <section id="chaveamento" class="knockout-bracket">
      <h2>Chaveamento</h2>
      <p class="bracket-note">Mata-mata organizado em dois lados que convergem para a final e o campeao.</p>
      <div class="bracket-scroll" aria-label="Chaveamento do mata-mata da Copa do Mundo">
        <div class="bracket-grid">
{left_rounds}
          <div class="bracket-center">
            <div class="bracket-round-title">Final</div>
            {html_bracket_final(final_match)}
            {html_bracket_champion(final_match)}
          </div>
{right_rounds}
        </div>
      </div>
    </section>"""


def knockout_bracket_rounds(
    matches: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    rounds: dict[str, list[dict[str, Any]]] = {
        stage: [] for stage in KNOCKOUT_BRACKET_STAGES
    }
    for match in matches:
        stage = str(match.get("stage") or "")
        if match.get("group") != "Sem grupo" or stage not in rounds:
            continue
        rounds[stage].append(match)

    for stage_matches in rounds.values():
        stage_matches.sort(
            key=lambda match: (
                datetime.fromisoformat(match["date"]),
                str(match.get("home") or ""),
                str(match.get("away") or ""),
            )
        )
    return rounds


def split_bracket_matches(
    matches: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    middle = (len(matches) + 1) // 2
    return matches[:middle], matches[middle:]


def html_bracket_round(
    stage: str,
    matches: list[dict[str, Any]],
    side: str,
) -> str:
    cards = (
        "\n".join(html_bracket_match_card(match) for match in matches)
        if matches
        else """          <div class="bracket-placeholder">Aguardando confrontos</div>"""
    )
    return f"""          <div class="bracket-round {escape_html(side)}">
            <div class="bracket-round-title">{escape_html(stage)}</div>
{cards}
          </div>"""


def html_bracket_final(match: dict[str, Any] | None) -> str:
    if match is None:
        return """<div class="bracket-placeholder">Final a definir</div>"""
    return html_bracket_match_card(match, extra_class="bracket-final-card")


def html_bracket_champion(match: dict[str, Any] | None) -> str:
    winner = bracket_match_winner(match) if match else None
    champion = (
        html_team_label(winner["name"], winner.get("logo"))
        if winner is not None
        else "A definir"
    )
    return f"""<div class="bracket-champion">
              <div>
                <span>Campeao</span>
                <strong>{champion}</strong>
              </div>
            </div>"""


def html_bracket_match_card(
    match: dict[str, Any],
    extra_class: str = "",
) -> str:
    when = datetime.fromisoformat(match["date"]).astimezone().strftime("%d/%m %H:%M")
    venue = match.get("venue") or "Local a definir"
    status = bracket_status_label(match)
    winner = bracket_match_winner(match)
    home_winner = winner is not None and winner["side"] == "home"
    away_winner = winner is not None and winner["side"] == "away"
    score_visible = match["completed"] or str(match.get("state", "")).lower() == "in"
    score = (
        f"{match['home_score']} x {match['away_score']}"
        if score_visible
        else "x"
    )
    pairing_text = f"{match['home']} {score} {match['away']}"

    return f"""          <article class="bracket-match {escape_html(extra_class)}" aria-label="{escape_html(pairing_text)}">
            <div class="bracket-meta">
              <span>{escape_html(when)}</span>
              <span>{escape_html(venue)}</span>
            </div>
            {html_bracket_team(match["home"], match.get("home_logo"), match["home_score"], home_winner, score_visible)}
            {html_bracket_team(match["away"], match.get("away_logo"), match["away_score"], away_winner, score_visible)}
            <div class="bracket-status">{escape_html(status)}</div>
          </article>"""


def html_bracket_team(
    name: object,
    logo: object,
    score_value: object,
    is_winner: bool,
    score_visible: bool,
) -> str:
    winner_class = " winner" if is_winner else ""
    score_text = escape_html(score_value) if score_visible else ""
    return f"""<div class="bracket-team{winner_class}">
              {html_team_label(name, logo)}
              <span class="bracket-score">{score_text}</span>
            </div>"""


def bracket_status_label(match: dict[str, Any]) -> str:
    if match["completed"]:
        return "Encerrado"
    if str(match.get("state", "")).lower() == "in":
        return "Ao vivo"
    return "Agendado"


def bracket_match_winner(match: dict[str, Any] | None) -> dict[str, str] | None:
    if not match or not match["completed"]:
        return None
    if match["home_score"] > match["away_score"]:
        return {
            "side": "home",
            "name": str(match["home"]),
            "logo": str(match.get("home_logo") or ""),
        }
    if match["away_score"] > match["home_score"]:
        return {
            "side": "away",
            "name": str(match["away"]),
            "logo": str(match.get("away_logo") or ""),
        }
    return None


def html_summary_cards(
    matches: list[dict[str, Any]],
    completed: list[dict[str, Any]],
    upcoming: list[dict[str, Any]],
    leader_label: str,
) -> str:
    cards = [
        ("Jogos", str(len(matches))),
        ("Encerrados", str(len(completed))),
        ("Proximos", str(len(upcoming))),
        ("Melhor campanha", leader_label),
    ]
    items = "\n".join(f"""      <article class="card">
        <span>{escape_html(title)}</span>
        <strong>{escape_html(value)}</strong>
      </article>""" for title, value in cards)
    return f"""    <section id="resumo">
      <h2>Resumo</h2>
      <div class="cards">
{items}
      </div>
    </section>"""


def html_dashboard_toc() -> str:
    links = [
        ("Resumo", "#resumo"),
        ("Placar agora", "#placar-agora"),
        ("Proximas etapas", "#proximas-etapas"),
        ("Chaveamento", "#chaveamento"),
        ("Tabela dos grupos", "#tabela-grupos"),
        ("Proximos jogos", "#proximos-jogos"),
        ("Resultados recentes", "#resultados-recentes"),
    ]
    items = "\n".join(
        f"""        <a href="{escape_html(target)}">{escape_html(label)}</a>"""
        for label, target in links
    )
    return f"""    <nav class="toc" aria-label="Sumario do dashboard">
      <h2>Sumario</h2>
      <div class="toc-links">
{items}
      </div>
    </nav>"""


def html_live_scoreboard(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return """    <section id="placar-agora">
      <h2>Placar agora</h2>
      <p class="empty">Nenhum jogo em andamento agora.</p>
    </section>"""

    items = "\n".join(html_live_match_card(match) for match in matches)
    return f"""    <section id="placar-agora">
      <h2>Placar agora</h2>
      <div class="live-scoreboards">
{items}
      </div>
    </section>"""


def html_live_match_card(match: dict[str, Any]) -> str:
    when = datetime.fromisoformat(match["date"]).astimezone().strftime("%d/%m/%Y %H:%M")
    stage = (
        f"Grupo {match['group']}"
        if match["group"] != "Sem grupo"
        else str(match.get("stage") or "Mata-mata")
    )
    venue = match.get("venue") or "Local a definir"
    detail = match.get("detail") or "Em andamento"
    pairing_text = (
        f"{match['home']} {match['home_score']} x "
        f"{match['away_score']} {match['away']}"
    )
    return f"""        <article class="live-scoreboard">
        <div class="live-meta">
          <span class="live-badge">Agora</span>
          <span>{escape_html(stage)}</span>
          <span>{escape_html(when)}</span>
          <span>{escape_html(venue)}</span>
        </div>
        <div class="live-teams" aria-label="{escape_html(pairing_text)}">
          {html_live_team(match["home"], match.get("home_logo"), match["home_score"])}
          <span class="live-versus">x</span>
          {html_live_team(match["away"], match.get("away_logo"), match["away_score"])}
        </div>
        <div class="live-detail">{escape_html(detail)}</div>
      </article>"""


def html_live_team(name: object, logo: object, goals: object) -> str:
    return f"""<div class="live-team">
            {html_team_label(name, logo)}
            <strong>{escape_html(goals)}</strong>
          </div>"""


def html_stage_dashboard(summaries: list[StageSummary]) -> str:
    pending_stages = [summary for summary in summaries if summary.pending > 0]
    if not pending_stages:
        message = (
            "Todas as etapas encontradas no periodo consultado ja foram encerradas."
            if summaries
            else "Nenhuma etapa encontrada no periodo consultado."
        )
        return f"""    <section id="proximas-etapas">
      <h2>Proximas etapas</h2>
      <p class="empty">{escape_html(message)}</p>
    </section>"""

    rows = "\n".join(f"""          <tr>
            <td class="stage">{escape_html(summary.stage)}</td>
            <td>{escape_html(format_stage_period(summary))}</td>
            <td>{summary.total}</td>
            <td class="status-ok">{summary.completed}</td>
            <td class="status-next">{summary.upcoming}</td>
            <td>{escape_html(format_stage_highlight(summary))}</td>
          </tr>""" for summary in pending_stages)
    return f"""    <section id="proximas-etapas">
      <h2>Proximas etapas</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Etapa</th>
              <th>Periodo</th>
              <th>Jogos</th>
              <th>Encerrados</th>
              <th>Proximos</th>
              <th>Destaque</th>
            </tr>
          </thead>
          <tbody>
{rows}
          </tbody>
        </table>
      </div>
    </section>"""


def html_group_tables(tables: dict[str, list[TeamStats]]) -> str:
    if not tables:
        return """    <section id="tabela-grupos">
      <h2>Tabela dos grupos</h2>
      <p class="empty">Sem jogos encerrados no periodo consultado.</p>
    </section>"""

    sections = []
    for group, teams in tables.items():
        rows = "\n".join(f"""            <tr>
              <td>{position}</td>
              <td class="team">{html_team_label(team.name, team.logo)}</td>
              <td>{team.played}</td>
              <td>{team.wins}</td>
              <td>{team.draws}</td>
              <td>{team.losses}</td>
              <td>{team.goals_for}</td>
              <td>{team.goals_against}</td>
              <td>{team.goal_difference:+d}</td>
              <td>{team.points}</td>
            </tr>""" for position, team in enumerate(teams, start=1))
        sections.append(f"""      <h3>Grupo {escape_html(group)}</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Pos</th>
              <th>Time</th>
              <th>J</th>
              <th>V</th>
              <th>E</th>
              <th>D</th>
              <th>GP</th>
              <th>GC</th>
              <th>SG</th>
              <th>Pts</th>
            </tr>
          </thead>
          <tbody>
{rows}
          </tbody>
        </table>
      </div>""")

    return f"""    <section id="tabela-grupos">
      <h2>Tabela dos grupos</h2>
{chr(10).join(sections)}
    </section>"""


def html_match_section(
    title: str,
    matches: list[dict[str, Any]],
    include_score: bool,
) -> str:
    section_id = match_section_id(title)
    if not matches:
        return f"""    <section id="{escape_html(section_id)}">
      <h2>{escape_html(title)}</h2>
      <p class="empty">Nenhum jogo encontrado no periodo consultado.</p>
    </section>"""

    items = "\n".join(html_match_card(match, include_score) for match in matches)
    return f"""    <section id="{escape_html(section_id)}">
      <h2>{escape_html(title)}</h2>
      <div class="matches">
{items}
      </div>
    </section>"""


def match_section_id(title: str) -> str:
    if title == "Proximos jogos":
        return "proximos-jogos"
    if title == "Resultados recentes":
        return "resultados-recentes"
    return "jogos"


def html_match_card(match: dict[str, Any], include_score: bool) -> str:
    when = datetime.fromisoformat(match["date"]).astimezone().strftime("%d/%m/%Y %H:%M")
    stage = (
        f"Grupo {match['group']}"
        if match["group"] != "Sem grupo"
        else str(match.get("stage") or "Mata-mata")
    )
    if include_score:
        pairing_text = (
            f"{match['home']} {match['home_score']} x "
            f"{match['away_score']} {match['away']}"
        )
        pairing = (
            f"{html_team_label(match['home'], match.get('home_logo'))} "
            f"<span>{match['home_score']} x {match['away_score']}</span> "
            f"{html_team_label(match['away'], match.get('away_logo'))}"
        )
    else:
        pairing_text = f"{match['home']} x {match['away']}"
        pairing = (
            f"{html_team_label(match['home'], match.get('home_logo'))} "
            f"<span>x</span> "
            f"{html_team_label(match['away'], match.get('away_logo'))}"
        )
    venue = match.get("venue") or "Local a definir"
    detail = match.get("detail") or ""
    return f"""        <article class="match">
          <div class="match-top">
            <span>{escape_html(when)}</span>
            <span>{escape_html(stage)}</span>
            <span>{escape_html(venue)}</span>
          </div>
          <div class="score" aria-label="{escape_html(pairing_text)}">{pairing}</div>
          <div>{escape_html(detail)}</div>
        </article>"""


def html_team_label(name: object, logo: object = "") -> str:
    label = escape_html(name)
    source = str(logo or "").strip()
    if not source:
        return f"""<span class="team-label">{label}</span>"""
    return (
        f"""<span class="team-label">"""
        f"""<img class="team-flag" src="{escape_html(source)}" alt="">"""
        f"""{label}</span>"""
    )


def escape_html(value: object) -> str:
    return html.escape(str(value), quote=True)


def write_html_dashboard(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path.resolve()


def dashboard_header(source_label: str, selected_group: str | None) -> list[str]:
    width = 96
    title = "COPA DO MUNDO 2026 - DASHBOARD"
    updated = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    group = selected_group.upper() if selected_group else "Todos"
    lines = [
        "+" + "-" * (width - 2) + "+",
        f"| {title:<54} Atualizado: {updated:<22} |",
        f"| Fonte: {fit_text(source_label, 53):<53} Grupo: {group:<25} |",
        "+" + "-" * (width - 2) + "+",
        "",
    ]
    return lines


def append_dashboard_summary(
    lines: list[str],
    matches: list[dict[str, Any]],
    tables: dict[str, list[TeamStats]],
    completed: list[dict[str, Any]],
    upcoming: list[dict[str, Any]],
    selected_group: str | None,
) -> None:
    selected = selected_group.upper() if selected_group else None
    visible_tables = {
        group: teams
        for group, teams in tables.items()
        if selected in (None, group.upper())
    }
    leader = best_campaign(visible_tables)
    leader_label = (
        f"{leader.name} ({leader.points} pts)" if leader is not None else "Sem dados"
    )
    cards = [
        ("Jogos", str(len(matches))),
        ("Encerrados", str(len(completed))),
        ("Proximos", str(len(upcoming))),
        ("Melhor campanha", leader_label),
    ]

    lines.append("Resumo")
    lines.append(
        "+----------------------+----------------------+----------------------+----------------------+"
    )
    lines.append("| " + " | ".join(f"{title:<20}" for title, _ in cards) + " |")
    lines.append(
        "| " + " | ".join(f"{fit_text(value, 20):<20}" for _, value in cards) + " |"
    )
    lines.append(
        "+----------------------+----------------------+----------------------+----------------------+"
    )
    lines.append("")


def append_stage_dashboard(lines: list[str], summaries: list[StageSummary]) -> None:
    append_section_title(lines, "Proximas etapas")
    pending_stages = [summary for summary in summaries if summary.pending > 0]

    if not pending_stages:
        if summaries:
            lines.append(
                "Todas as etapas encontradas no periodo consultado ja foram encerradas."
            )
        else:
            lines.append("Nenhuma etapa encontrada no periodo consultado.")
        lines.append("")
        return

    lines.append(
        "+----------------------+-------------+-------+-----------+----------+----------------------------+"
    )
    lines.append(
        "| Etapa                | Periodo     | Jogos | Encerr.   | Prox.    | Destaque                   |"
    )
    lines.append(
        "+----------------------+-------------+-------+-----------+----------+----------------------------+"
    )
    for summary in pending_stages:
        lines.append(
            f"| {fit_text(summary.stage, 20):<20} "
            f"| {format_stage_period(summary):<11} "
            f"| {summary.total:>5} "
            f"| {summary.completed:>9} "
            f"| {summary.upcoming:>8} "
            f"| {fit_text(format_stage_highlight(summary), 26):<26} |"
        )
    lines.append(
        "+----------------------+-------------+-------+-----------+----------+----------------------------+"
    )
    lines.append("")


def format_stage_period(summary: StageSummary) -> str:
    if summary.first_date is None:
        return "-"

    first = summary.first_date.astimezone().strftime("%d/%m")
    if (
        summary.last_date is None
        or summary.last_date.date() == summary.first_date.date()
    ):
        return first
    last = summary.last_date.astimezone().strftime("%d/%m")
    return f"{first}-{last}"


def format_stage_highlight(summary: StageSummary) -> str:
    if summary.next_match is None:
        return "Aguardando jogo futuro" if summary.pending > 0 else "Concluida"

    match_date = datetime.fromisoformat(summary.next_match["date"]).astimezone()
    pairing = f"{summary.next_match['home']} x {summary.next_match['away']}"
    return f"{match_date:%d/%m %H:%M} {pairing}"


def best_campaign(tables: dict[str, list[TeamStats]]) -> TeamStats | None:
    teams = [team for group_teams in tables.values() for team in group_teams]
    if not teams:
        return None
    return sorted(teams, key=team_sort_key)[0]


def append_tables(
    lines: list[str],
    tables: dict[str, list[TeamStats]],
    selected_group: str | None,
) -> None:
    selected = selected_group.upper() if selected_group else None
    groups = {
        group: teams
        for group, teams in tables.items()
        if selected in (None, group.upper())
    }

    if not groups:
        append_section_title(lines, "Tabela dos grupos")
        lines.append("Sem jogos encerrados no periodo consultado.")
        lines.append("")
        return

    append_section_title(lines, "Tabela dos grupos")
    for group, teams in groups.items():
        lines.append(f"Grupo {group}")
        lines.append(
            "+-----+----------------------+----+----+----+----+----+----+-----+-----+"
        )
        lines.append(
            "| Pos | Time                 | J  | V  | E  | D  | GP | GC | SG  | Pts |"
        )
        lines.append(
            "+-----+----------------------+----+----+----+----+----+----+-----+-----+"
        )
        for position, team in enumerate(teams, start=1):
            lines.append(
                f"| {position:>3} | {fit_text(team.name, 20):<20} "
                f"| {team.played:>2} | {team.wins:>2} | {team.draws:>2} | "
                f"{team.losses:>2} | {team.goals_for:>2} | {team.goals_against:>2} | "
                f"{team.goal_difference:>+3} | {team.points:>3} |"
            )
        lines.append(
            "+-----+----------------------+----+----+----+----+----+----+-----+-----+"
        )
        lines.append("")
    lines.append("")


def append_recent_results(lines: list[str], matches: list[dict[str, Any]]) -> None:
    append_section_title(lines, "Resultados recentes")
    if not matches:
        lines.append("Nenhum resultado encerrado no periodo consultado.")
        lines.append("")
        return

    for match in matches:
        lines.append(format_match(match))
    lines.append("")


def append_upcoming(lines: list[str], matches: list[dict[str, Any]]) -> None:
    append_section_title(lines, "Proximos jogos")
    if not matches:
        lines.append("Nenhum jogo futuro encontrado no periodo consultado.")
        lines.append("")
        return

    for match in matches:
        lines.append(format_match(match, include_score=False))
    lines.append("")


def format_match(match: dict[str, Any], include_score: bool = True) -> str:
    when = datetime.fromisoformat(match["date"]).astimezone().strftime("%d/%m %H:%M")
    stage = (
        f"Grupo {match['group']}"
        if match["group"] != "Sem grupo"
        else str(match.get("stage") or "Mata-mata")
    )
    if include_score:
        pairing = (
            f"{match['home']} {match['home_score']} x "
            f"{match['away_score']} {match['away']}"
        )
    else:
        pairing = f"{match['home']} x {match['away']}"

    detail = f" - {match['detail']}" if match.get("detail") else ""
    return f"{when} | {stage:<16} | {pairing}{detail}"


def append_section_title(lines: list[str], title: str) -> None:
    lines.append(title)
    lines.append("-" * len(title))


def fit_text(value: object, width: int) -> str:
    text = str(value)
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def run_once(args: argparse.Namespace) -> str:
    end = min(parse_iso_date(args.data), TOURNAMENT_END)
    start = max(parse_iso_date(args.inicio), TOURNAMENT_START)
    cache_path = Path(args.cache)
    data, source_label = load_scoreboard(start, end, cache_path, not args.sem_cache)
    events = data.get("events", [])
    tables = build_group_tables(events)

    if args.json:
        return (
            json.dumps(
                normalized_payload(events, tables),
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )

    if args.html:
        html_path = write_html_dashboard(
            Path(args.html),
            render_html(
                data,
                source_label,
                args.grupo,
                max(args.recentes, 0),
                max(args.proximos, 0),
            ),
        )
        return f"Dashboard HTML gerado em: {html_path}\n"

    return render(
        data,
        source_label,
        args.grupo,
        max(args.recentes, 0),
        max(args.proximos, 0),
    )


def main() -> int:
    args = parse_args()

    if args.watch is None:
        print(run_once(args), end="")
        return 0

    interval = max(args.watch, 10)
    try:
        while True:
            os.system("clear")
            print(run_once(args), end="")
            print(f"\nAtualizando a cada {interval}s. Pressione Ctrl+C para sair.")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nEncerrado.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
