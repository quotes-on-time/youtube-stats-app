import streamlit as st
import csv
import pandas as pd
import time
from urllib.parse import urlparse
from googleapiclient.discovery import build
import math

# Fetch the API key and password from Streamlit Secrets
API_KEY = st.secrets["API_KEY"]
PASSWORD = st.secrets["APP_PASSWORD"]

def extract_handle_from_url(url):
    parsed_url = urlparse(url)
    path = parsed_url.path
    if path.startswith('/@'):
        return path[1:]
    else:
        st.error(f"Invalid YouTube handle URL: {url}")
        return None

def get_channel_stats(youtube, handles):
    request = youtube.channels().list(
        part='statistics',
        forHandle=",".join(handles)   # multiple handles in one request
    )
    response = request.execute()
    results = {}
    if 'items' in response:
        for item in response['items']:
            stats = item['statistics']
            channel_id = item['id']
            results[channel_id] = {
                "Subscribers": stats.get('subscriberCount', 'N/A'),
                "Videos": stats.get('videoCount', 'N/A')
            }
    return results

def main():
    st.title("YouTube Stats Checker")

    # Login screen
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        password = st.text_input("Enter password to access the app:", type="password")
        if password == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.warning("Please enter the correct password to proceed.")
            st.stop()

    # Initialize session state
    if "results" not in st.session_state:
        st.session_state.results = []
    if "urls" not in st.session_state:
        st.session_state.urls = []
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0

    uploaded_file = st.file_uploader("Upload CSV file with YouTube channel URLs")

    if uploaded_file and not st.session_state.processing:
        lines = uploaded_file.read().decode('utf-8').splitlines()
        reader = csv.reader(lines)
        st.session_state.urls = [row[0].strip() for row in reader if row]
        st.session_state.results = []
        st.session_state.current_index = 0

    # New input: channels per request
    batch_size = st.number_input("Channels per request (1–50):", min_value=1, max_value=50, value=1, step=1)

    if st.button("Start Processing") and st.session_state.urls:
        st.session_state.processing = True

    if st.session_state.processing:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        total_rows = len(st.session_state.urls)
        total_batches = math.ceil(total_rows / batch_size)
        progress_bar = st.progress(st.session_state.current_index / total_rows)
        progress_text = st.empty()

        for idx in range(st.session_state.current_index, total_rows, batch_size):
            batch_urls = st.session_state.urls[idx:idx + batch_size]
            handles = [extract_handle_from_url(url) for url in batch_urls if extract_handle_from_url(url)]

            if handles:
                try:
                    stats_dict = get_channel_stats(youtube, handles)
                    for url, handle in zip(batch_urls, handles):
                        st.session_state.results.append({
                            "Channel URL": url,
                            "Subscribers": stats_dict.get(handle, {}).get("Subscribers", "N/A"),
                            "Videos": stats_dict.get(handle, {}).get("Videos", "N/A")
                        })
                except Exception as e:
                    st.error(f"Error processing {handles}: {str(e)}")
                    for url in batch_urls:
                        st.session_state.results.append({
                            "Channel URL": url,
                            "Subscribers": "Error",
                            "Videos": "Error"
                        })

            st.session_state.current_index = idx + batch_size
            progress_bar.progress(min(st.session_state.current_index / total_rows, 1.0))
            progress_text.text(f"Progress: {(st.session_state.current_index / total_rows) * 100:.2f}%")

            time.sleep(1)  # pacing: 1 request per second

        st.session_state.processing = False

    if st.session_state.results:
        st.write("### Results (showing first 4 rows):")
        df = pd.DataFrame(st.session_state.results)
        st.table(df.head(4))

        csv_filename = "youtube_stats_results.csv"
        df.to_csv(csv_filename, index=False)

        st.success(f"Results saved to {csv_filename}.")
        st.download_button(
            label="Download CSV",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=csv_filename,
            mime='text/csv'
        )

if __name__ == "__main__":
    main()
