import csv
import sys
import re
import os
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import string

class CSVFileManager:
    def __init__(self, input_file_path, output_file_path, flush_path):
        self.input_file_path = input_file_path
        self.output_file_path = output_file_path
        self.flush_path = flush_path

    def read_emails(self):
        emails = []
        with open(self.input_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                emails.append(row)
        return emails

    def read_processed_emails(self):
        try:
            with open(self.output_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                return [row for row in reader]
        except FileNotFoundError:
            return []

    def append_emails(self, emails):
        with open(self.output_file_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=emails[0].keys())
            if file.tell() == 0:  # Check if file is empty to write header
                writer.writeheader()
            for email in emails:
                writer.writerow(email)
    
    def flush_emails(self, new_emails):
        new_emails = pd.DataFrame(new_emails)
        file_exists = os.path.isfile(self.flush_path) and os.path.getsize(self.flush_path) > 0

        all_emails = pd.read_csv(self.input_file_path)
        emails_to_flush = all_emails[all_emails['MessageID'].isin(new_emails['MessageID'])]
        emails_to_flush.to_csv(self.flush_path, mode='a', header=not file_exists, index=False)

        filtered_all_emails = all_emails[~all_emails['MessageID'].isin(new_emails['MessageID'])]
        filtered_all_emails.to_csv(self.input_file_path, index=False)

        print("Emails Flushed")

class EmailProcessor:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()

    def refine_text(self, body):
        if bool(BeautifulSoup(body, "html.parser").find()):
            soup = BeautifulSoup(body, "html.parser")
            text = soup.get_text(separator="\n")
        else:
            text = body.strip()
        url_pattern = r'https?://\S+|www\.\S+'
        text = re.sub(url_pattern, '', text)
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        text = re.sub(r'<.*?>', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        text = re.sub(r'\b\w\b', '', text)
        text = re.sub(r'\d+', '', text)
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        text = re.sub(r'\S*@\S*\s?', '', text)
        text = re.sub(f"[{string.punctuation}]", "", text)
        text = re.sub(r'\s+', ' ', text).strip()
        tokens = word_tokenize(text)
        tokens = [self.lemmatizer.lemmatize(word) for word in tokens]
        return ' '.join(tokens)
    
    def convert_to_utc(self, dt):
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            return dt.replace(tzinfo=timezone.utc)
        else:
            return dt.astimezone(timezone.utc)
    
    def fit_hypothesis(self, email):
        return 'The email is from: "'+ email['From']+ '". The email subject: "' + email['Subject'] + '". -end of the email subject. The email body: "' + email['Body']+ '" -end of the email body. '

    def process_emails(self, emails, processed_emails):
        processed_emails_ids = {email['MessageID'] for email in processed_emails}
        new_emails = [email for email in emails if email['MessageID'] not in processed_emails_ids]
        for email in new_emails:
            email['Body'] = self.refine_text(email['Body'])
            email['Subject'] = self.refine_text(email['Subject'])
            email['text'] = self.fit_hypothesis(email)
            try:
                parsed_date = parsedate_to_datetime(email['Date'])
                email['ParsedDate'] = self.convert_to_utc(parsed_date)
            except (ValueError, KeyError):
                email['ParsedDate'] = self.convert_to_utc(datetime(1970, 1, 1))
        new_emails.sort(key=lambda x: x['ParsedDate'])
        return new_emails

def set_max_csv_field_size():
    max_int = sys.maxsize
    while True:
        try:
            csv.field_size_limit(max_int)
            break
        except OverflowError:
            max_int = int(max_int/10)

def main():
    set_max_csv_field_size()
    emails_path = 'mail/emails.csv'
    output_path = 'processEmails/processed_emails.csv'
    flush_path = 'mail/flushed_emails.csv'

    file_manager = CSVFileManager(emails_path, output_path, flush_path)
    all_emails = file_manager.read_emails()
    processed_emails = file_manager.read_processed_emails()

    email_processor = EmailProcessor()
    new_emails = email_processor.process_emails(all_emails, processed_emails)

    if new_emails:
        file_manager.append_emails(new_emails)
        print(f"Processed and saved {len(new_emails)} new emails.")
        file_manager.flush_emails(new_emails)
    else:
        print("No new emails to process.")

if __name__ == "__main__":
    main()
