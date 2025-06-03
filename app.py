import streamlit as st
import csv
import pandas as pd
import time
from urllib.parse import urlparse
from googleapiclient.discovery import build

# Fetch the API key from Streamlit Secrets
API_KEY = st.secrets["API_KEY"]

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
    uploaded_file = st.file_uploader("Upload CSV file with YouTube channel URLs")

    if uploaded_file:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        lines = uploaded_file.read().decode('utf-8').splitlines()
        reader = csv.reader(lines)
        urls = [row[0].strip() for row in reader if row]

        if st.button("Start Processing"):
            results = []
            total_rows = len(urls)
            progress_bar = st.progress(0)
            progress_text = st.empty()  # Placeholder for percentage text

            for idx, url in enumerate(urls):
                handle = extract_handle_from_url(url)
                if handle:
                    try:
                        subs, vids = get_channel_stats(youtube, handle)
                    except Exception as e:
                        st.error(f"Error processing {handle}: {str(e)}")
                        subs, vids = 'Error', 'Error'
                    
                    results.append({
                        "Channel URL": url,
                        "Subscribers": subs,
                        "Videos": vids
                    })

                    time.sleep(1)  # 1 request per second

                progress_percentage = ((idx + 1) / total_rows) * 100
                progress_bar.progress((idx + 1) / total_rows)
                progress_text.text(f"Progress: {progress_percentage:.2f}%")

            st.write("### Results (showing first 4 rows):")
            df = pd.DataFrame(results)
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
