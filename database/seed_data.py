"""Generate synthetic streaming-platform CSV data in data_sources/."""
import random
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

OUT = Path(__file__).parent / "data_sources"  # database/data_sources/
OUT.mkdir(exist_ok=True)

# ── movies ──────────────────────────────────────────────────────────────────
genres = ["Action", "Comedy", "Drama", "Thriller", "Sci-Fi", "Romance", "Horror", "Documentary"]
ratings = ["G", "PG", "PG-13", "R"]
languages = ["English", "Spanish", "French", "Hindi", "Korean", "Japanese"]
directors = [
    "James Cameron", "Sofia Coppola", "Christopher Nolan", "Greta Gerwig",
    "Bong Joon-ho", "Steven Spielberg", "Ava DuVernay", "Denis Villeneuve",
    "Jordan Peele", "Patty Jenkins",
]
n_movies = 200
movies = pd.DataFrame({
    "movie_id": [f"M{i:04d}" for i in range(1, n_movies + 1)],
    "title": [f"Title {i}" for i in range(1, n_movies + 1)],
    "genre": np.random.choice(genres, n_movies),
    "release_year": np.random.randint(2015, 2026, n_movies),
    "director": np.random.choice(directors, n_movies),
    "runtime_minutes": np.random.randint(75, 180, n_movies),
    "budget_usd": np.random.randint(1_000_000, 200_000_000, n_movies),
    "box_office_usd": np.random.randint(500_000, 500_000_000, n_movies),
    "rating": np.random.choice(ratings, n_movies, p=[0.05, 0.15, 0.45, 0.35]),
    "language": np.random.choice(languages, n_movies, p=[0.55, 0.15, 0.08, 0.10, 0.07, 0.05]),
})
movies.to_csv(OUT / "movies.csv", index=False)

# ── viewers ──────────────────────────────────────────────────────────────────
countries = ["US", "UK", "India", "Canada", "Germany", "Brazil", "Australia", "France"]
tiers = ["Free", "Basic", "Premium"]
devices = ["Mobile", "Desktop", "TV", "Tablet"]
n_viewers = 500
join_dates = pd.date_range("2021-01-01", "2024-12-31", periods=n_viewers)
viewers = pd.DataFrame({
    "viewer_id": [f"V{i:04d}" for i in range(1, n_viewers + 1)],
    "age": np.random.randint(16, 70, n_viewers),
    "gender": np.random.choice(["M", "F", "Other"], n_viewers, p=[0.46, 0.46, 0.08]),
    "country": np.random.choice(countries, n_viewers, p=[0.35, 0.12, 0.18, 0.08, 0.07, 0.08, 0.06, 0.06]),
    "subscription_tier": np.random.choice(tiers, n_viewers, p=[0.30, 0.35, 0.35]),
    "join_date": [d.date() for d in join_dates],
    "preferred_device": np.random.choice(devices, n_viewers, p=[0.40, 0.25, 0.25, 0.10]),
})
viewers.to_csv(OUT / "viewers.csv", index=False)

# ── watch_activity ────────────────────────────────────────────────────────────
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
completed = [1 if d >= runtimes[mid] * 0.9 else 0
             for d, mid in zip(watch_durations, activity_movie_ids)]
watch_dates = pd.date_range("2023-01-01", "2024-12-31", periods=n_activity)
watch_activity = pd.DataFrame({
    "activity_id": [f"A{i:05d}" for i in range(1, n_activity + 1)],
    "viewer_id": activity_viewer_ids,
    "movie_id": activity_movie_ids,
    "watch_date": [d.date() for d in watch_dates],
    "watch_duration_minutes": watch_durations,
    "completed": completed,
    "platform": np.random.choice(devices, n_activity, p=[0.40, 0.25, 0.25, 0.10]),
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
    "review_id": [f"R{i:05d}" for i in range(1, n_reviews + 1)],
    "viewer_id": rev_viewer_ids,
    "movie_id": rev_movie_ids,
    "star_rating": star_ratings,
    "review_date": [d.date() for d in review_dates],
    "sentiment": sentiments,
    "helpful_votes": np.random.randint(0, 200, n_reviews),
})
reviews.to_csv(OUT / "reviews.csv", index=False)

# ── marketing_spend ───────────────────────────────────────────────────────────
channels = ["Social Media", "Email", "TV", "Search", "Display"]
months = pd.date_range("2023-01-01", "2024-12-01", freq="MS")
rows = []
for month in months:
    for channel in channels:
        spend = round(np.random.uniform(10_000, 250_000), 2)
        impressions = int(spend * np.random.uniform(50, 200))
        ctr = np.random.uniform(0.01, 0.08)
        clicks = int(impressions * ctr)
        conv_rate = np.random.uniform(0.02, 0.15)
        conversions = int(clicks * conv_rate)
        cpa = round(spend / max(conversions, 1), 2)
        rows.append({
            "month": month.date(),
            "channel": channel,
            "spend_usd": spend,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "cpa_usd": cpa,
        })
marketing_spend = pd.DataFrame(rows)
marketing_spend.to_csv(OUT / "marketing_spend.csv", index=False)

# ── regional_performance ──────────────────────────────────────────────────────
regions = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]
rows = []
for month in months:
    for region in regions:
        new_subs = np.random.randint(500, 8000)
        churned = np.random.randint(100, int(new_subs * 0.3))
        revenue = round(new_subs * np.random.uniform(8, 20), 2)
        avg_watch = round(np.random.uniform(45, 180), 1)
        content_hours = round(new_subs * avg_watch / 60, 1)
        rows.append({
            "month": month.date(),
            "region": region,
            "new_subscribers": new_subs,
            "churned_subscribers": churned,
            "net_subscriber_change": new_subs - churned,
            "revenue_usd": revenue,
            "avg_watch_minutes": avg_watch,
            "content_hours_watched": content_hours,
        })
regional_performance = pd.DataFrame(rows)
regional_performance.to_csv(OUT / "regional_performance.csv", index=False)

print("Generated:")
for f in sorted(OUT.glob("*.csv")):
    df = pd.read_csv(f)
    print(f"  {f.name}: {len(df)} rows x {len(df.columns)} cols")
