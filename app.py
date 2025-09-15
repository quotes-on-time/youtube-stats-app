import streamlit as st
import csv
import pandas as pd
import time
from urllib.parse import urlparse
from googleapiclient.discovery import build

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

def get_channel_stats(youtube, handle):
    request = youtube.channels().list(
        part='statistics',
        forHandle=handle
    )
    response = request.execute()
    if 'items' not in response or len(response['items']) == 0:
        return None, None
    stats = response['items'][0]['statistics']
    return stats.get('subscriberCount', 'N/A'), stats.get('videoCount', 'N/A')

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

    batch_size = st.number_input("How many channels to request per run?", min_value=1, max_value=50, value=1, step=1)

    if uploaded_file and not st.session_state.processing:
        lines = uploaded_file.read().decode('utf-8').splitlines()
        reader = csv.reader(lines)
        st.session_state.urls = [row[0].strip() for row in reader if row]
        st.session_state.results = []
        st.session_state.current_index = 0

    if st.button("Start Processing") and st.session_state.urls:
        st.session_state.processing = True

    if st.session_state.processing:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        total_rows = len(st.session_state.urls)
        progress_bar = st.progress(st.session_state.current_index / total_rows)
        progress_text = st.empty()

        while st.session_state.current_index < total_rows:
            batch_end = min(st.session_state.current_index + batch_size, total_rows)
            batch = st.session_state.urls[st.session_state.current_index:batch_end]

            for url in batch:
                handle = extract_handle_from_url(url)
                if handle:
                    try:
                        subs, vids = get_channel_stats(youtube, handle)
                    except Exception as e:
                        st.error(f"Error processing {handle}: {str(e)}")
                        subs, vids = 'Error', 'Error'

                    st.session_state.results.append({
                        "Channel URL": url,
                        "Subscribers": subs,
                        "Videos": vids
                    })

                st.session_state.current_index += 1
                progress_bar.progress(st.session_state.current_index / total_rows)
                progress_text.text(f"Progress: {(st.session_state.current_index / total_rows) * 100:.2f}%")
                time.sleep(1)  # Maintain 1 request per second

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
