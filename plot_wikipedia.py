import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import Counter
from datetime import datetime
import time
import os
import json
import sys
import argparse

def get_cache_filename(title):
    # Construct Wikipedia URL from title
    wiki_url = f'https://en.wikipedia.org/wiki/{title.replace(" ", "_")}'
    # Make filename resemble the link structure using dashes as separator
    safe_url = wiki_url.replace('https://', 'https-').replace('/', '-').replace(':', '-').replace('.', '-').replace('?', '-').replace('"', '-').replace('<', '-').replace('>', '-').replace('|', '-')
    return os.path.join('cache', f"{safe_url}.json")

def load_cached_dates(title):
    cache_file = get_cache_filename(title)
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            dates = json.load(f)
            return sorted(dates)  # ensure sorted
    return []

def save_cached_dates(title, dates):
    cache_file = get_cache_filename(title)
    os.makedirs('cache', exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(sorted(dates), f)

def get_revision_dates(title):
    """Fetch all revision timestamps for a Wikipedia page, updating cache"""
    cached_dates = load_cached_dates(title)
    dates = cached_dates[:]

    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvprop": "timestamp|userid",
        "rvlimit": "500",
        "format": "json",
        "rvdir": "newer",
        "continue": ""
    }

    if cached_dates:
        last_date = cached_dates[-1]
        params["rvstart"] = last_date + "T00:00:00Z"

    fetched_dates = []
    print(f"Fetching revisions for: {title}")
    if cached_dates:
        print(f" (updating from cache, last date: {last_date})")

    while True:
        headers = {'User-Agent': 'WikiPlot/1.0 (https://github.com/yourname/wikiplot)'}
        response = requests.get(url, params=params, headers=headers).json()

        if "query" not in response or "pages" not in response["query"]:
            print("Error: Page not found or invalid response")
            break

        page_id = list(response["query"]["pages"].keys())[0]
        revisions = response["query"]["pages"][page_id].get("revisions", [])

        for rev in revisions:
            timestamp = rev["timestamp"][:10]  # YYYY-MM-DD
            fetched_dates.append(timestamp)

        print(f"Fetched {len(dates) + len(fetched_dates)} revisions so far...", end="\r")

        if "continue" not in response:
            break
        params["continue"] = response["continue"]["continue"]
        params["rvcontinue"] = response["continue"]["rvcontinue"]

        time.sleep(0.2)  # Be nice to Wikipedia

    # Filter new dates
    if cached_dates:
        last_date = cached_dates[-1]
        new_dates = [d for d in fetched_dates if d > last_date]
    else:
        new_dates = fetched_dates

    dates.extend(new_dates)
    print(f"\nDone! Total revisions: {len(dates)} ({len(new_dates)} new)")
    if new_dates or not cached_dates:
        save_cached_dates(title, dates)
    return dates


def plot_edit_history(dates, title, log_base=10, user_input=None):
    # Dark mode style
    plt.style.use('dark_background')

    # Count edits per day
    daily_counts = Counter(dates)

    # Sort by date
    sorted_dates = sorted(daily_counts.keys())
    counts = [daily_counts[date] for date in sorted_dates]
    # Convert to datetime for better plotting
    date_objects = [datetime.strptime(d, "%Y-%m-%d") for d in sorted_dates]
    # Convert datetimes to Matplotlib's numeric format to satisfy type hints
    date_nums = mdates.date2num(date_objects)

    plt.figure(figsize=(16, 6))
    plt.yscale('log', base=log_base)
    bars = plt.bar(date_nums, counts, width=1.0, color='steelblue', edgecolor='none', align='center')

    # Highlight days with many edits
    max_edits = max(counts)
    peak_date = sorted_dates[counts.index(max_edits)]
    for bar, count in zip(bars, counts):
        if count > max_edits * 0.6:  # top 40% tallest
            bar.set_color('red')
            bar.set_alpha(0.8)

    wiki_url = f'https://en.wikipedia.org/wiki/{title.replace(" ", "_")}'
    # Multi-line title with colored link
    plt.title(f"Total edits: {len(dates)} | Peak: {peak_date} ({max_edits} edits) | Red bars = busiest editing days", fontsize=12, pad=30)
    plt.figtext(0.5, 0.90, f"Plot Graph (Log Scale base: {log_base}) that represents the amount of edits in the wikipedia article over time at", ha='center', fontsize=12, color='white')
    plt.figtext(0.5, 0.82, wiki_url, ha='center', fontsize=14, color='royalblue')
    plt.ylabel(f"Log (base {log_base}) Number of edits in one day")
    plt.xlabel("Year")
    ax = plt.gca()
    ax.xaxis_date()
    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    # Add command used
    script_name = os.path.basename(sys.argv[0])
    if user_input:
        if log_base != 10:
            cmd = f"python {script_name} {repr(user_input)} --log {log_base}"
        else:
            cmd = f"python {script_name} {repr(user_input)}"
    else:
        cmd = f"python {script_name}"
    plt.figtext(0.01, 0.01, f'Command: {cmd}', fontsize=10, color='gray')

    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()

    # Save figure with custom filename in plotGraphs folder
    os.makedirs('plotGraphs', exist_ok=True)
    safe_filename = os.path.join('plotGraphs', title.replace(" ", "_").replace("/", "_").replace("\\", "_") + "_edit_history.png")
    plt.savefig(safe_filename, dpi=300, bbox_inches='tight', facecolor='black', edgecolor='black')
    print(f"\nPlot saved as: {safe_filename}")

    plt.show()


# ============== USAGE ==============
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot Wikipedia page edit history.')
    parser.add_argument('input', nargs='?', help='Wikipedia page title or URL')
    parser.add_argument('--log', type=float, default=10, help='Logarithmic base for y-axis (default: 10)')

    args = parser.parse_args()

    user_input = args.input
    if user_input is None:
        user_input = input("Enter Wikipedia page title or URL: ").strip()

    if "wikipedia.org" in user_input:
        title = user_input.split("/wiki/")[-1].split("#")[0].replace("_", " ")
    else:
        title = user_input.replace(" ", "_")

    dates = get_revision_dates(title)
    plot_edit_history(dates, title.replace("_", " "), args.log, user_input)
