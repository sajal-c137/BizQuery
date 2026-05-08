"""Generate synthetic streaming-platform CSV data in data_sources/.

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

OUT = Path(__file__).parent / "data_sources"  # database/data_sources/
OUT.mkdir(exist_ok=True)

# ── shared dimensions ────────────────────────────────────────────────────────
GENRES = ["Action", "Comedy", "Drama", "Thriller", "Sci-Fi", "Romance", "Horror", "Documentary"]
REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]
TIERS = ["Free", "Basic", "Premium"]
DEVICES = ["Mobile", "Desktop", "TV", "Tablet"]
RATINGS = ["G", "PG", "PG-13", "R"]
CHANNELS = ["Social Media", "Email", "TV Ad", "Search", "Display"]

# Country → region mapping (used in viewers and movies)
COUNTRY_TO_REGION = {
    "US":           "North America",
    "Canada":       "North America",
    "UK":           "Europe",
    "Germany":      "Europe",
    "France":       "Europe",
    "India":        "Asia Pacific",
    "Australia":    "Asia Pacific",
    "South Korea":  "Asia Pacific",
    "Brazil":       "Latin America",
    "Mexico":       "Latin America",
    "UAE":          "Middle East & Africa",
    "South Africa": "Middle East & Africa",
}
COUNTRIES = list(COUNTRY_TO_REGION.keys())
COUNTRY_WEIGHTS = [0.25, 0.07, 0.10, 0.06, 0.05, 0.11, 0.05, 0.06, 0.07, 0.05, 0.04, 0.09]

# Production country per region (movies are produced predominantly in one region)
REGION_COUNTRIES = {
    "North America":        ["US", "Canada"],
    "Europe":               ["UK", "Germany", "France"],
    "Asia Pacific":         ["India", "South Korea", "Australia"],
    "Latin America":        ["Brazil", "Mexico"],
    "Middle East & Africa": ["UAE", "South Africa"],
}

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

# Assign production_country: bias toward region that matches language
prod_countries = []
for lang in np.random.choice(LANGUAGES, n_movies, p=[0.50, 0.12, 0.08, 0.12, 0.10, 0.08]):
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
    else:  # Japanese
        prod_countries.append(np.random.choice(["Japan", "South Korea"], p=[0.7, 0.3]))

# Japan isn't in our viewer countries but is a valid production country — map it to Asia Pacific
COUNTRY_TO_REGION["Japan"] = "Asia Pacific"

movies = pd.DataFrame({
    "movie_id":           [f"M{i:04d}" for i in range(1, n_movies + 1)],
    "title":              [f"Title {i}" for i in range(1, n_movies + 1)],
    "genre":              movie_genres,
    "release_year":       np.random.randint(2015, 2026, n_movies),
    "director":           np.random.choice(DIRECTORS, n_movies),
    "runtime_minutes":    np.random.randint(75, 180, n_movies),
    "budget_usd":         np.random.randint(1_000_000, 200_000_000, n_movies),
    "box_office_usd":     np.random.randint(500_000, 500_000_000, n_movies),
    "content_rating":     np.random.choice(RATINGS, n_movies, p=[0.05, 0.15, 0.45, 0.35]),
    "language":           np.random.choice(LANGUAGES, n_movies, p=[0.50, 0.12, 0.08, 0.12, 0.10, 0.08]),
    "production_country": prod_countries,
})
# Derive production_region for direct joining with regional_performance
movies["production_region"] = movies["production_country"].map(COUNTRY_TO_REGION)
movies.to_csv(OUT / "movies.csv", index=False)

# ── viewers ──────────────────────────────────────────────────────────────────
n_viewers = 500
join_dates = pd.date_range("2021-01-01", "2024-12-31", periods=n_viewers)
viewer_countries = np.random.choice(COUNTRIES, n_viewers, p=COUNTRY_WEIGHTS)

viewers = pd.DataFrame({
    "viewer_id":        [f"V{i:04d}" for i in range(1, n_viewers + 1)],
    "age":              np.random.randint(16, 70, n_viewers),
    "gender":           np.random.choice(["M", "F", "Other"], n_viewers, p=[0.46, 0.46, 0.08]),
    "country":          viewer_countries,
    "region":           [COUNTRY_TO_REGION[c] for c in viewer_countries],  # pre-joined for convenience
    "subscription_tier": np.random.choice(TIERS, n_viewers, p=[0.30, 0.35, 0.35]),
    "join_date":        [d.date() for d in join_dates],
    "preferred_device": np.random.choice(DEVICES, n_viewers, p=[0.40, 0.25, 0.25, 0.10]),
})
viewers.to_csv(OUT / "viewers.csv", index=False)

# ── watch_activity ───────────────────────────────────────────────────────────
n_activity = 2000
movie_ids = movies["movie_id"].values
viewer_ids = viewers["viewer_id"].values
activity_movie_ids = np.random.choice(movie_ids, n_activity)
activity_viewer_ids = np.random.choice(viewer_ids, n_activity)
runtimes = movies.set_index("movie_id")["runtime_minutes"]
watch_durations = [
    int(min(runtimes[mid] * np.random.uniform(0.1, 1.05), runtimes[mid]))
    for mid in activity_movie_ids
]
completed = [
    1 if d >= runtimes[mid] * 0.9 else 0
    for d, mid in zip(watch_durations, activity_movie_ids)
]
watch_dates = pd.date_range("2023-01-01", "2024-12-31", periods=n_activity)

watch_activity = pd.DataFrame({
    "activity_id":           [f"A{i:05d}" for i in range(1, n_activity + 1)],
    "viewer_id":             activity_viewer_ids,
    "movie_id":              activity_movie_ids,
    "watch_date":            [d.date() for d in watch_dates],
    "month":                 [d.strftime("%Y-%m-01") for d in watch_dates],  # FK → marketing_spend/regional_performance
    "watch_duration_minutes": watch_durations,
    "completed":             completed,
    "platform":              np.random.choice(DEVICES, n_activity, p=[0.40, 0.25, 0.25, 0.10]),
})
watch_activity.to_csv(OUT / "watch_activity.csv", index=False)

# ── reviews ──────────────────────────────────────────────────────────────────
n_reviews = 1000
rev_viewer_ids = np.random.choice(viewer_ids, n_reviews)
rev_movie_ids = np.random.choice(movie_ids, n_reviews)
star_ratings = np.random.choice([1, 2, 3, 4, 5], n_reviews, p=[0.05, 0.10, 0.20, 0.35, 0.30])
sentiments = [
    "Positive" if r >= 4 else ("Negative" if r <= 2 else "Neutral")
    for r in star_ratings
]
review_dates = pd.date_range("2023-01-01", "2024-12-31", periods=n_reviews)

reviews = pd.DataFrame({
    "review_id":    [f"R{i:05d}" for i in range(1, n_reviews + 1)],
    "viewer_id":    rev_viewer_ids,
    "movie_id":     rev_movie_ids,
    "star_rating":  star_ratings,
    "review_date":  [d.date() for d in review_dates],
    "month":        [d.strftime("%Y-%m-01") for d in review_dates],  # FK → marketing_spend/regional_performance
    "sentiment":    sentiments,
    "helpful_votes": np.random.randint(0, 200, n_reviews),
})
reviews.to_csv(OUT / "reviews.csv", index=False)

# ── marketing_spend ──────────────────────────────────────────────────────────
# Grain: one row per (month, region, channel, genre_target)
# Joins: regional_performance on (month, region); movies on genre_target=genre
rows = []
for month in MONTHS:
    for region in REGIONS:
        for channel in CHANNELS:
            genre_target = np.random.choice(GENRES)
            spend = round(np.random.uniform(5_000, 120_000), 2)
            impressions = int(spend * np.random.uniform(50, 200))
            ctr = np.random.uniform(0.01, 0.08)
            clicks = int(impressions * ctr)
            conv_rate = np.random.uniform(0.02, 0.15)
            conversions = int(clicks * conv_rate)
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
# Grain: one row per (month, region)
# Joins: marketing_spend on (month, region); viewers via viewers.region
rows = []
for month in MONTHS:
    for region in REGIONS:
        new_subs = np.random.randint(500, 8_000)
        churned = np.random.randint(100, max(101, int(new_subs * 0.3)))
        revenue = round(new_subs * np.random.uniform(8, 20), 2)
        avg_watch = round(np.random.uniform(45, 180), 1)
        content_hours = round(new_subs * avg_watch / 60, 1)
        rows.append({
            "month":                 month.date(),
            "region":                region,
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

print("\nRelational keys:")
print("  movie_id  : movies <-> watch_activity <-> reviews")
print("  viewer_id : viewers <-> watch_activity <-> reviews")
print("  country->region : viewers.region -> regional_performance.region")
print("  production_country->region : movies.production_region -> regional_performance.region")
print("  (month, region) : marketing_spend <-> regional_performance")
print("  genre : movies.genre <-> marketing_spend.genre_target")
print("  month : watch_activity.month <-> marketing_spend.month <-> regional_performance.month")
