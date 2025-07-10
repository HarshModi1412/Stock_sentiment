import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv('merged_Senti.csv')

    df['created_at'] = pd.to_datetime(
        df['created_at'],
        format='%a %b %d %H:%M:%S %z %Y',
        errors='coerce'
    )

    df['likes'] = pd.to_numeric(df.get('likes', 0), errors='coerce').fillna(0).astype(int)
    df['sentiment_scores'] = pd.to_numeric(df.get('sentiment_scores', 0), errors='coerce').fillna(0)
    df.dropna(subset=['created_at'], inplace=True)

    return df


# Perform multi-word AND search
def multi_word_search_and(df, column, query):
    words = [w.strip() for w in re.split(r'[\s,]+', query.lower()) if w]
    mask = pd.Series(True, index=df.index)
    for w in words:
        mask &= df[column].str.lower().str.contains(w, na=False)
    return df[mask]


# Compute sentiment stats
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


# Streamlit UI
st.set_page_config(page_title="Sentiment News Analyzer", layout="wide")
st.title("📰 Sentiment News Dashboard")

df = load_data()

# Search and sort options
query = st.text_input("Search (source/text keywords)", value="")
sort_by = st.radio("Sort by:", ['date', 'likes'], horizontal=True)

# Filter
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

# Compute stats
stats = compute_stats(filtered)

# Display stats
st.subheader("📊 Summary Stats")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Entries", stats["total_entries"])
col2.metric("Avg Sentiment (6 days)", stats["avg_sentiment"])
col3.metric("Sentiment (yesterday)", stats["six_day_sentiment"])
col4.metric("Date Range", stats["date_range"])

# Daily scores
with st.expander("📅 Daily Sentiment (Last 6 Days)"):
    for day, score in stats["daily_scores"]:
        st.write(f"**{day}**: {score}")

# Display news
st.subheader("🗞️ Filtered News")
if filtered.empty:
    st.warning("No results found. Try different keywords.")
else:
    for _, row in filtered.iterrows():
        st.markdown(f"### [{row.get('source', 'Unknown')}]({row.get('url', '#')})")
        st.write(f"**Date**: {row['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"**Sentiment**: {round(row['sentiment_scores'], 2)}")
        st.write(f"**Likes**: {row['likes']}")
        st.write(row.get('text', ''))
        st.markdown("---")
