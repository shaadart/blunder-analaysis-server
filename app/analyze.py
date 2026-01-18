#!/usr/bin/env python3
"""Analyze PGN file for chess game statistics.

Usage:
  python3 analyze.py --username myusername --pgn-file moves.pgn

This script parses a PGN file, determines wins/losses/draws for the specified user,
and analyzes performance by time of day, day of week, and month.
"""

import argparse
import chess.pgn
import collections
from datetime import datetime
from typing import Optional, Dict, Counter
import matplotlib.pyplot as plt
import os


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Analyze PGN file for chess game statistics.")
    p.add_argument("--username", required=True, help="Your Lichess username to identify your games")
    p.add_argument("--pgn-file", default="moves.pgn", help="Path to PGN file (default: moves.pgn)")
    return p.parse_args()


def determine_result_for_user(game: chess.pgn.Game, username: str) -> Optional[str]:
    """Return 'win', 'loss', or 'draw' for the user, or None if not playing."""
    white = game.headers.get("White", "").lower()
    black = game.headers.get("Black", "").lower()
    result = game.headers.get("Result", "")
    user_lower = username.lower()

    if white == user_lower:
        if result == "1-0":
            return "win"
        elif result == "0-1":
            return "loss"
        elif result == "1/2-1/2":
            return "draw"
    elif black == user_lower:
        if result == "0-1":
            return "win"
        elif result == "1-0":
            return "loss"
        elif result == "1/2-1/2":
            return "draw"
    return None  # User not in this game


def parse_datetime(game: chess.pgn.Game) -> Optional[datetime]:
    """Parse date and time from PGN headers."""
    date_str = game.headers.get("UTCDate", game.headers.get("Date", ""))
    time_str = game.headers.get("UTCTime", game.headers.get("Time", ""))
    try:
        if time_str:
            dt_str = f"{date_str} {time_str}"
            return datetime.strptime(dt_str, "%Y.%m.%d %H:%M:%S")
        else:
            return datetime.strptime(date_str, "%Y.%m.%d")
    except ValueError:
        return None


def analyze_games(pgn_file: str, username: str) -> Dict:
    """Analyze the PGN file and return stats."""
    results: Counter[str] = collections.Counter()
    hour_stats: Counter[int] = collections.Counter()
    weekday_stats: Counter[int] = collections.Counter()  # 0=Monday, 6=Sunday
    month_stats: Counter[int] = collections.Counter()  # 1-12

    with open(pgn_file, "r", encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            result = determine_result_for_user(game, username)
            if result is None:
                continue  # Skip games not involving the user

            results[result] += 1

            dt = parse_datetime(game)
            if dt:
                hour_stats[dt.hour] += 1
                weekday_stats[dt.weekday()] += 1
                month_stats[dt.month] += 1

    # Calculate win rates for each category
    def win_rate(counter: Counter[int], results_per_key: Dict[int, Counter[str]]) -> Dict[int, float]:
        rates = {}
        for key in counter:
            total = sum(results_per_key.get(key, {}).values())
            wins = results_per_key.get(key, {}).get("win", 0)
            rates[key] = wins / total if total > 0 else 0
        return rates

    # But we need results per key, so collect them
    hour_results: Dict[int, Counter[str]] = collections.defaultdict(collections.Counter)
    weekday_results: Dict[int, Counter[str]] = collections.defaultdict(collections.Counter)
    month_results: Dict[int, Counter[str]] = collections.defaultdict(collections.Counter)

    # Re-parse to collect per-key results
    with open(pgn_file, "r", encoding="utf-8") as f:
        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            result = determine_result_for_user(game, username)
            if result is None:
                continue

            dt = parse_datetime(game)
            if dt:
                hour_results[dt.hour][result] += 1
                weekday_results[dt.weekday()][result] += 1
                month_results[dt.month][result] += 1

    hour_win_rates = win_rate(hour_stats, hour_results)
    weekday_win_rates = win_rate(weekday_stats, weekday_results)
    month_win_rates = win_rate(month_stats, month_results)

    return {
        "total_games": sum(results.values()),
        "wins": results["win"],
        "losses": results["loss"],
        "draws": results["draw"],
        "best_hour": max(hour_win_rates, key=hour_win_rates.get, default=None),
        "worst_hour": min(hour_win_rates, key=hour_win_rates.get, default=None),
        "most_productive_weekday": max(weekday_win_rates, key=weekday_win_rates.get, default=None),
        "most_productive_month": max(month_win_rates, key=month_win_rates.get, default=None),
        "hour_win_rates": hour_win_rates,
        "weekday_win_rates": weekday_win_rates,
        "month_win_rates": month_win_rates,
    }


def main() -> int:
    args = parse_args()
    try:
        stats = analyze_games(args.pgn_file, args.username)
    except FileNotFoundError:
        print(f"Error: PGN file '{args.pgn_file}' not found.")
        return 1
    except Exception as e:
        print(f"Error analyzing PGN: {e}")
        return 1

    print("Chess Game Analysis")
    print("===================")
    print(f"Total games: {stats['total_games']}")
    print(f"Wins: {stats['wins']}")
    print(f"Losses: {stats['losses']}")
    print(f"Draws: {stats['draws']}")

    if stats['best_hour'] is not None:
        print(f"\nBest time of day (hour): {stats['best_hour']}:00 (win rate: {stats['hour_win_rates'][stats['best_hour']]:.2%})")
        print(f"Worst time of day (hour): {stats['worst_hour']}:00 (win rate: {stats['hour_win_rates'][stats['worst_hour']]:.2%})")

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if stats['most_productive_weekday'] is not None:
        wd = stats['most_productive_weekday']
        print(f"Most productive day of week: {weekdays[wd]} (win rate: {stats['weekday_win_rates'][wd]:.2%})")

    months = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    if stats['most_productive_month'] is not None:
        m = stats['most_productive_month']
        print(f"Most productive month: {months[m]} (win rate: {stats['month_win_rates'][m]:.2%})")

    # Generate visualizations
    plots_dir = "plots"
    os.makedirs(plots_dir, exist_ok=True)

    # Pie chart for results
    if stats['total_games'] > 0:
        labels = ['Wins', 'Losses', 'Draws']
        sizes = [stats['wins'], stats['losses'], stats['draws']]
        colors = ['green', 'red', 'gray']
        plt.figure(figsize=(6, 6))
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
        plt.title('Game Results')
        plt.savefig(os.path.join(plots_dir, 'results_pie.png'))
        plt.close()

    # Bar chart for hour win rates
    if stats['hour_win_rates']:
        hours = sorted(stats['hour_win_rates'].keys())
        rates = [stats['hour_win_rates'][h] * 100 for h in hours]
        plt.figure(figsize=(10, 5))
        plt.bar(hours, rates, color='blue')
        plt.xlabel('Hour of Day')
        plt.ylabel('Win Rate (%)')
        plt.title('Win Rate by Hour')
        plt.xticks(hours)
        plt.savefig(os.path.join(plots_dir, 'hour_win_rates.png'))
        plt.close()

    # Bar chart for weekday win rates
    if stats['weekday_win_rates']:
        wds = sorted(stats['weekday_win_rates'].keys())
        wd_labels = [weekdays[wd] for wd in wds]
        rates = [stats['weekday_win_rates'][wd] * 100 for wd in wds]
        plt.figure(figsize=(10, 5))
        plt.bar(wd_labels, rates, color='purple')
        plt.xlabel('Day of Week')
        plt.ylabel('Win Rate (%)')
        plt.title('Win Rate by Day of Week')
        plt.savefig(os.path.join(plots_dir, 'weekday_win_rates.png'))
        plt.close()

    # Bar chart for month win rates
    if stats['month_win_rates']:
        ms = sorted(stats['month_win_rates'].keys())
        m_labels = [months[m] for m in ms]
        rates = [stats['month_win_rates'][m] * 100 for m in ms]
        plt.figure(figsize=(10, 5))
        plt.bar(m_labels, rates, color='orange')
        plt.xlabel('Month')
        plt.ylabel('Win Rate (%)')
        plt.title('Win Rate by Month')
        plt.savefig(os.path.join(plots_dir, 'month_win_rates.png'))
        plt.close()

    print(f"\nVisualizations saved to '{plots_dir}/' directory.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())