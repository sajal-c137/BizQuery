"""Generate synthetic streaming-platform CSV data in data_sources/.

Magnitudes are tuned for a mid-sized streaming platform (multi-million subs,
hundreds of millions in revenue, real CPM/CPA ranges).

Relational keys
---------------
movie_id        : movies  <->  watch_activity  <->  reviews
viewer_id       : viewers <->  watch_activity  <->  reviews
country->region : viewers.country  ->  regional_performance.region
                  movies.production_country -> regional_performance.region
region+month    : marketing_spend <-> regional_performance  (direct join)
genre           : movies.genre    <-> marketing_spend.genre_target
month           : watch_activity (by month) <-> marketing_spend <-> regional_performance
"""
import random
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

OUT = Path(__file__).parent / "data_sources"
OUT.mkdir(exist_ok=True)

# ── shared dimensions ────────────────────────────────────────────────────────
GENRES = ["Action", "Comedy", "Drama", "Thriller", "Sci-Fi", "Romance", "Horror", "Documentary"]
REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]
TIERS = ["Free", "Basic", "Premium"]
DEVICES = ["Mobile", "Desktop", "TV", "Tablet"]
RATINGS = ["G", "PG", "PG-13", "R"]
CHANNELS = ["Social Media", "Email", "TV Ad", "Search", "Display"]

COUNTRY_TO_REGION = {
    "US":           "North America",
    "Canada":       "North America",
    "UK":           "Europe",
    "Germany":      "Europe",
    "France":       "Europe",
    "India":        "Asia Pacific",
    "Australia":    "Asia Pacific",
    "South Korea":  "Asia Pacific",
    "Japan":        "Asia Pacific",
    "Brazil":       "Latin America",
    "Mexico":       "Latin America",
    "UAE":          "Middle East & Africa",
    "South Africa": "Middle East & Africa",
}
COUNTRIES = [c for c in COUNTRY_TO_REGION if c != "Japan"]
COUNTRY_WEIGHTS = [0.25, 0.07, 0.10, 0.06, 0.05, 0.11, 0.05, 0.06, 0.07, 0.05, 0.04, 0.09]

MONTHS = pd.date_range("2023-01-01", "2024-12-01", freq="MS")

# ── movies ───────────────────────────────────────────────────────────────────
DIRECTORS = [
    "James Cameron", "Sofia Coppola", "Christopher Nolan", "Greta Gerwig",
    "Bong Joon-ho", "Steven Spielberg", "Ava DuVernay", "Denis Villeneuve",
    "Jordan Peele", "Patty Jenkins",
]
LANGUAGES = ["English", "Spanish", "French", "Hindi", "Korean", "Japanese"]

n_movies = 200
movie_genres = np.random.choice(GENRES, n_movies)
movie_languages = np.random.choice(LANGUAGES, n_movies, p=[0.50, 0.12, 0.08, 0.12, 0.10, 0.08])

prod_countries = []
for lang in movie_languages:
    if lang == "English":
        prod_countries.append(np.random.choice(["US", "UK", "Australia", "Canada"]))
    elif lang == "Spanish":
        prod_countries.append(np.random.choice(["Mexico", "Brazil"], p=[0.6, 0.4]))
    elif lang == "French":
        prod_countries.append("France")
    elif lang == "Hindi":
        prod_countries.append("India")
    elif lang == "Korean":
        prod_countries.append("South Korea")
    else:
        prod_countries.append(np.random.choice(["Japan", "South Korea"], p=[0.7, 0.3]))

# Lognormal so most films cluster around the median; a few are blockbusters / flops.
budgets = np.clip(np.random.lognormal(mean=np.log(25_000_000), sigma=0.9, size=n_movies),
                  500_000, 300_000_000).astype(int)
bo_multipliers = np.random.lognormal(mean=np.log(1.7), sigma=0.9, size=n_movies)
box_offices = np.clip(budgets * bo_multipliers, 0, 2_000_000_000).astype(int)

movies = pd.DataFrame({
    "movie_id":           [f"M{i:04d}" for i in range(1, n_movies + 1)],
    "title":              [f"Title {i}" for i in range(1, n_movies + 1)],
    "genre":              movie_genres,
    "release_year":       np.random.randint(2015, 2026, n_movies),
    "director":           np.random.choice(DIRECTORS, n_movies),
    "runtime_minutes":    np.random.randint(75, 180, n_movies),
    "budget_usd":         budgets,
    "box_office_usd":     box_offices,
    "content_rating":     np.random.choice(RATINGS, n_movies, p=[0.05, 0.15, 0.45, 0.35]),
    "language":           movie_languages,
    "production_country": prod_countries,
})
movies["production_region"] = movies["production_country"].map(COUNTRY_TO_REGION)
movies.to_csv(OUT / "movies.csv", index=False)

# ── viewers ──────────────────────────────────────────────────────────────────
n_viewers = 500
join_dates = pd.date_range("2021-01-01", "2024-12-31", periods=n_viewers)
viewer_countries = np.random.choice(COUNTRIES, n_viewers, p=COUNTRY_WEIGHTS)
ages = np.clip(np.random.normal(loc=34, scale=12, size=n_viewers), 13, 80).astype(int)

viewers = pd.DataFrame({
    "viewer_id":         [f"V{i:04d}" for i in range(1, n_viewers + 1)],
    "age":               ages,
    "gender":            np.random.choice(["M", "F", "Other"], n_viewers, p=[0.46, 0.46, 0.08]),
    "country":           viewer_countries,
    "region":            [COUNTRY_TO_REGION[c] for c in viewer_countries],
    "subscription_tier": np.random.choice(TIERS, n_viewers, p=[0.20, 0.45, 0.35]),
    "join_date":         [d.date() for d in join_dates],
    "preferred_device":  np.random.choice(DEVICES, n_viewers, p=[0.40, 0.20, 0.30, 0.10]),
})
viewers.to_csv(OUT / "viewers.csv", index=False)

# ── watch_activity ───────────────────────────────────────────────────────────
n_activity = 2000
movie_ids = movies["movie_id"].values
viewer_ids = viewers["viewer_id"].values
activity_movie_ids = np.random.choice(movie_ids, n_activity)
activity_viewer_ids = np.random.choice(viewer_ids, n_activity)
runtimes = movies.set_index("movie_id")["runtime_minutes"]

# Bimodal: ~55% near-complete, rest partial. Completion rate lands ~50%.
watch_durations = []
completed = []
for mid in activity_movie_ids:
    rt = int(runtimes[mid])
    frac = np.random.uniform(0.80, 1.0) if np.random.random() < 0.55 else np.random.uniform(0.05, 0.70)
    watch_durations.append(int(rt * frac))
    completed.append(1 if frac >= 0.9 else 0)

watch_dates = pd.date_range("2023-01-01", "2024-12-31", periods=n_activity)

watch_activity = pd.DataFrame({
    "activity_id":            [f"A{i:05d}" for i in range(1, n_activity + 1)],
    "viewer_id":              activity_viewer_ids,
    "movie_id":               activity_movie_ids,
    "watch_date":             [d.date() for d in watch_dates],
    "month":                  [d.strftime("%Y-%m-01") for d in watch_dates],
    "watch_duration_minutes": watch_durations,
    "completed":              completed,
    "platform":               np.random.choice(DEVICES, n_activity, p=[0.40, 0.20, 0.30, 0.10]),
})
watch_activity.to_csv(OUT / "watch_activity.csv", index=False)

# ── reviews ──────────────────────────────────────────────────────────────────
n_reviews = 1000
rev_viewer_ids = np.random.choice(viewer_ids, n_reviews)
rev_movie_ids = np.random.choice(movie_ids, n_reviews)
star_ratings = np.random.choice([1, 2, 3, 4, 5], n_reviews, p=[0.05, 0.10, 0.20, 0.35, 0.30])
sentiments = ["Positive" if r >= 4 else ("Negative" if r <= 2 else "Neutral") for r in star_ratings]
review_dates = pd.date_range("2023-01-01", "2024-12-31", periods=n_reviews)
# Long-tail helpful votes — most reviews get a handful, occasional ones go viral.
helpful_votes = np.clip(np.random.lognormal(mean=1.5, sigma=1.4, size=n_reviews), 0, 5000).astype(int)

reviews = pd.DataFrame({
    "review_id":     [f"R{i:05d}" for i in range(1, n_reviews + 1)],
    "viewer_id":     rev_viewer_ids,
    "movie_id":      rev_movie_ids,
    "star_rating":   star_ratings,
    "review_date":   [d.date() for d in review_dates],
    "month":         [d.strftime("%Y-%m-01") for d in review_dates],
    "sentiment":     sentiments,
    "helpful_votes": helpful_votes,
})
reviews.to_csv(OUT / "reviews.csv", index=False)

# ── marketing_spend ──────────────────────────────────────────────────────────
# Per (month, region, channel, genre): spend $200K-$5M; CTR 0.5-3%; CVR 1-5%.
# Yields CPA in the realistic $20-$200 range.
rows = []
for month in MONTHS:
    for region in REGIONS:
        for channel in CHANNELS:
            genre_target = np.random.choice(GENRES)
            spend = round(np.random.uniform(200_000, 5_000_000), 2)
            cpm = np.random.uniform(5, 25)  # $ per 1000 impressions
            impressions = int(spend / cpm * 1000)
            ctr = np.random.uniform(0.005, 0.03)
            clicks = int(impressions * ctr)
            cvr = np.random.uniform(0.01, 0.05)
            conversions = int(clicks * cvr)
            cpa = round(spend / max(conversions, 1), 2)
            rows.append({
                "month":        month.date(),
                "region":       region,
                "channel":      channel,
                "genre_target": genre_target,
                "spend_usd":    spend,
                "impressions":  impressions,
                "clicks":       clicks,
                "conversions":  conversions,
                "cpa_usd":      cpa,
            })
marketing_spend = pd.DataFrame(rows)
marketing_spend.to_csv(OUT / "marketing_spend.csv", index=False)

# ── regional_performance ─────────────────────────────────────────────────────
# Subscriber base is in the millions; revenue computed from active subs * ARPU.
REGION_BASE_SUBS = {
    "North America":        4_500_000,
    "Europe":               3_200_000,
    "Asia Pacific":         2_400_000,
    "Latin America":        1_100_000,
    "Middle East & Africa":   450_000,
}
REGION_ARPU = {
    "North America":        14.50,
    "Europe":               10.80,
    "Asia Pacific":          6.50,
    "Latin America":         5.20,
    "Middle East & Africa":  4.40,
}

active_subs = dict(REGION_BASE_SUBS)
rows = []
for month in MONTHS:
    for region in REGIONS:
        base = active_subs[region]
        new_subs = int(base * np.random.uniform(0.030, 0.060))
        churned  = int(base * np.random.uniform(0.020, 0.040))
        active_subs[region] = base + new_subs - churned
        avg_active = (base + active_subs[region]) // 2
        revenue = round(avg_active * REGION_ARPU[region] * np.random.uniform(0.95, 1.05), 2)
        avg_watch = round(np.random.uniform(70, 120), 1)
        content_hours = round(avg_active * avg_watch / 60 * np.random.uniform(0.85, 1.15), 1)
        rows.append({
            "month":                 month.date(),
            "region":                region,
            "active_subscribers":    avg_active,
            "new_subscribers":       new_subs,
            "churned_subscribers":   churned,
            "net_subscriber_change": new_subs - churned,
            "revenue_usd":           revenue,
            "avg_watch_minutes":     avg_watch,
            "content_hours_watched": content_hours,
        })
regional_performance = pd.DataFrame(rows)
regional_performance.to_csv(OUT / "regional_performance.csv", index=False)

# ── summary ──────────────────────────────────────────────────────────────────
print("Generated:")
for f in sorted(OUT.glob("*.csv")):
    df = pd.read_csv(f)
    print(f"  {f.name}: {len(df)} rows x {len(df.columns)} cols")
