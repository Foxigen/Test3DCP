import os
import pickle
import base64
import pandas as pd
import time
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO
from google.auth.transport.requests import Request


# Function to decode base64 and save credentials to a file
def decode_credentials():
    # Get the base64-encoded credentials from Streamlit Secrets
    credentials_base64 = st.secrets["gdrive_credentials"]

    # Ensure that the base64 string is properly handled as a string, not bytes
    if isinstance(credentials_base64, bytes):
        credentials_json = base64.b64decode(credentials_base64).decode("utf-8")
    else:
        # If it's already a string, just decode it
        credentials_json = base64.b64decode(credentials_base64.encode("utf-8")).decode("utf-8")

    # Save the decoded credentials to a file
    with open("credentials.json", "w") as f:
        f.write(credentials_json)

# Define the Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Authenticate with Google Drive
def authenticate_google_drive():
    creds = None
    # Check if token.pickle exists (for saving access tokens)
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, perform OAuth 2.0 flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            decode_credentials()  # Decode credentials from Streamlit Secrets
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8501)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    return service

# Function to list files in a specific folder on Google Drive
def list_files(service, folder_id):
    results = service.files().list(
        q=f"'{folder_id}' in parents", 
        fields="files(id, name, createdTime)", 
        orderBy="createdTime desc"
    ).execute()
    return results.get('files', [])

# Function to download the latest file from Google Drive
def download_file_from_drive(service, file_id):
    request = service.files().get_media(fileId=file_id)
    file_name = f"downloaded_file.xlsx"
    fh = open(file_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.close()
    return file_name

# Streamlit app UI
st.title("Real-Time 3D Printing Data from Google Drive")

# Authenticate Google Drive
service = authenticate_google_drive()

# Google Drive folder ID (Replace with your folder ID)
folder_id = '12PxPdn6tYX3DJwCNKJRoTSsaQ2VtBECh'  # Replace with the actual folder ID

# Display the data table (initially empty)
data_placeholder = st.empty()

# Display the most recent files every 5 seconds
while True:
    # Get the list of files in the folder
    files = list_files(service, folder_id)

    if files:
        # Get the most recent file
        latest_file = files[0]
        st.write(f"Latest file: {latest_file['name']}")

        # Download the latest file
        file_name = download_file_from_drive(service, latest_file['id'])

        # Read the file with pandas
        data = pd.read_excel(file_name)

        # Display the data in the Streamlit table
        data_placeholder.dataframe(data)

    else:
        st.write("No files found.")

    # Wait for 5 seconds before checking for new updates
    time.sleep(5)
