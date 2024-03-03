import os.path
import base64
import pickle
import csv
import time
import sys
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

# Increase the maximum field size limit
csv.field_size_limit(max([sys.maxsize, 2147483647]))  # Max int value for 32/64 bit

class GmailService:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def __init__(self):
        self.service = self.get_gmail_service()

    def get_gmail_service(self):
        creds = None
        if os.path.exists('mail/token.pickle'):
            with open('mail/token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('mail/cred.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open('mail/token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        return build('gmail', 'v1', credentials=creds)

class EmailManager:
    def __init__(self, service):
        self.service = service

    @staticmethod
    def decode_mime_data(mime_data):
        try:
            byte_data = base64.urlsafe_b64decode(mime_data + '===')
            return byte_data.decode('utf-8')
        except Exception as e:
            print(f"Error decoding MIME data: {e}")
            return "Error decoding body."

    @staticmethod
    def get_email_body(parts, mime_type='text/plain'):
        if not parts:
            return ''
        for part in parts:
            if part['mimeType'] == mime_type:
                body_data = part['body'].get('data', '')
                if body_data:
                    return EmailManager.decode_mime_data(body_data)
            elif part['mimeType'] in ['multipart/alternative', 'multipart/related']:
                return EmailManager.get_email_body(part.get('parts', []), mime_type)
        return ''

    def get_email_details(self, msg_id, max_retries=3):
        for attempt in range(max_retries):
            try:
                msg = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
                headers = msg['payload']['headers']
                parts = msg.get('payload', {}).get('parts', [])
                body = ''
                if msg['payload']['mimeType'] in ['text/plain', 'text/html']:
                    body = self.decode_mime_data(msg['payload']['body'].get('data', ''))
                else:
                    body = self.get_email_body(parts, 'text/plain')
                    if not body:
                        body = self.get_email_body(parts, 'text/html')

                email_data = {
                    "MessageID": str(msg_id),
                    "From": next((header['value'] for header in headers if header['name'] == 'From'), "No Sender"),
                    "To": next((header['value'] for header in headers if header['name'] == 'To'), "No Recipient"),
                    "Subject": next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject"),
                    "Date": next((header['value'] for header in headers if header['name'] == 'Date'), "No Date"),
                    "Body": body
                }
                return email_data
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)
                    print(f"Retry {attempt + 1}/{max_retries} for email {msg_id} after error: {e}. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to get details for message {msg_id} after {max_retries} attempts: {e}")
        return None

class CSVManager:
    def __init__(self, service):
        self.service = service
        self.email_manager = EmailManager(service)

    @staticmethod
    def get_latest_email_date(csv_file):
        latest_date = None
        if os.path.exists(csv_file):
            with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                dates = [row['Date'] for row in reader if row['Date'] and row['Date'] != "No Date"]
                if dates:
                    try:
                        latest_date = max(parsedate_to_datetime(date).replace(tzinfo=ZoneInfo("UTC")) for date in dates)
                    except ValueError as e:
                        print(f"Error parsing date: {e}")
        return latest_date

    def save_emails_to_csv(self, start_date):
        csv_file = 'mail/emails.csv'
        fail_csv_file = 'mail/fail_emails.csv'
        latest_date = self.get_latest_email_date(csv_file)
        if not latest_date or latest_date <= start_date:
            latest_date = start_date
        else:
            latest_date += timedelta(seconds=1)
        query = f'after:{int(latest_date.timestamp())}'

        with open(csv_file, mode='a', newline='', encoding='utf-8') as file, \
             open(fail_csv_file, mode='a', newline='', encoding='utf-8') as fail_file:
            
            fieldnames = ['MessageID', 'From', 'To', 'Subject', 'Body', 'Date']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            fail_writer = csv.writer(fail_file)
            
            if os.stat(csv_file).st_size == 0:
                writer.writeheader()
            if os.stat(fail_csv_file).st_size == 0:
                fail_writer.writerow(['MessageID'])
            
            existing_ids = set()
            if os.path.exists(csv_file):
                with open(csv_file, mode='r', newline='', encoding='utf-8') as existing_file:
                    reader = csv.DictReader(existing_file)
                    existing_ids = {row['MessageID'] for row in reader}

            response = self.service.users().messages().list(userId='me', q=query).execute()
            while 'messages' in response:
                messages = response['messages']
                for msg in messages:
                    if msg['id'] not in existing_ids:
                        email_details = self.email_manager.get_email_details(msg['id'])
                        if email_details:
                            writer.writerow(email_details)
                            print(f"Added email {msg['id']} to CSV.")
                            existing_ids.add(msg['id'])
                        else:
                            fail_writer.writerow([msg['id']])
                            print(f"Failed email {msg['id']} recorded in fail_emails.csv.")
                if 'nextPageToken' in response:
                    page_token = response['nextPageToken']
                    response = self.service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
                else:
                    break
            
            if not messages:
                print("No new emails to add.")

    @staticmethod
    def email_exists_in_csv(csv_file, message_id):
        if os.path.exists(csv_file):
            with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if row['MessageID'] == message_id:
                        return True
        return False

    @staticmethod
    def report_emails_info(csv_file):
        if os.path.exists(csv_file):
            with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                email_count = sum(1 for row in reader)
                latest_date = CSVManager.get_latest_email_date(csv_file)
                if latest_date:
                    print(f"Number of emails in CSV: {email_count}")
                    print(f"Latest date fetched: {latest_date.strftime('%Y-%m-%d %H:%M:%S %z')}")
                else:
                    print("No emails in CSV.")

def main():
    gmail_service = GmailService().service
    csv_manager = CSVManager(gmail_service)
    start_date = datetime(2023, 12, 30, 23, 59, 59, tzinfo=ZoneInfo("UTC"))
    csv_manager.save_emails_to_csv(start_date)
    csv_manager.report_emails_info('mail/emails.csv')

if __name__ == '__main__':
    main()
