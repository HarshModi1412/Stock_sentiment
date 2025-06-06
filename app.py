from flask import Flask, render_template, request
import pandas as pd
import re
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Load data
def load_data():
    df = pd.read_csv('merged_Senti.csv')
    
    # Parse datetime
    df['created_at'] = pd.to_datetime(
        df['created_at'],
        format='%a %b %d %H:%M:%S %z %Y',
        errors='coerce'
    )
    
    # Clean numeric fields
    df['likes'] = pd.to_numeric(df.get('likes', 0), errors='coerce').fillna(0).astype(int)
    df['sentiment_scores'] = pd.to_numeric(df.get('sentiment_scores', 0), errors='coerce').fillna(0)

    # Drop rows with invalid dates
    df.dropna(subset=['created_at'], inplace=True)

    return df


# Perform multi-word AND search
def multi_word_search_and(df, column, query):
    words = [w.strip() for w in re.split(r'[\s,]+', query.lower()) if w]
    mask = pd.Series(True, index=df.index)
    for w in words:
        mask &= df[column].str.lower().str.contains(w, na=False)
    return df[mask]


# Compute daily and 6-day stats
def compute_stats(filtered_df):
    today = datetime.today().date()
    last_6_days = [today - timedelta(days=i) for i in range(1, 7)]
    daily_scores = []

    for day in reversed(last_6_days):
        day_df = filtered_df[filtered_df['created_at'].dt.date == day]
        if not day_df.empty:
            avg_sentiment = round(day_df['sentiment_scores'].mean(), 2)
            daily_scores.append((str(day), avg_sentiment))
        else:
            daily_scores.append((str(day), "Tweet not found"))

    six_day_df = filtered_df[filtered_df['created_at'].dt.date.isin(last_6_days)]
    avg_sentiment_last_6 = round(six_day_df['sentiment_scores'].mean(), 2) if not six_day_df.empty else "N/A"

    stats = {
        "avg_sentiment": avg_sentiment_last_6,
        "six_day_sentiment": daily_scores[0][1],
        "total_entries": len(filtered_df),
        "date_range": f"{filtered_df['created_at'].min().date()} to {filtered_df['created_at'].max().date()}" if not filtered_df.empty else "N/A",
        "daily_scores": daily_scores
    }
    return stats


@app.route('/')
def index():
    query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    df = load_data()

    # Filter based on query
    if query:
        filtered = multi_word_search_and(df, 'source', query)
        if filtered.empty:
            filtered = multi_word_search_and(df, 'text', query)
    else:
        filtered = df.copy()

    # Sort
    if sort_by == 'likes':
        filtered.sort_values(by='likes', ascending=False, inplace=True)
    else:
        filtered.sort_values(by='created_at', ascending=False, inplace=True)

    stats = compute_stats(filtered)

    # Format news items for frontend
    news_items = [
        {
            'Url': row.get('url', '#'),
            'source': row.get('source', 'Unknown'),
            'date': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(row['created_at']) else 'Unknown',
            'summary': row.get('text', ''),
            'sentiment': round(row.get('sentiment_scores', 0), 2),
            'likes': int(row.get('likes', 0))
        }
        for _, row in filtered.iterrows()
    ]

    return render_template(
        'index.html',
        news_items=news_items,
        query=query,
        sort_by=sort_by,
        stats=stats,
        no_results=len(news_items) == 0
    )


# Start app (Render compatible)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
