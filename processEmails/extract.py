import csv
import re
import os
import spacy
import joblib
import pandas as pd
from llm_inference import Model
from collections import Counter

class EmailProcessor:
    def __init__(self, ner_model="en_core_web_trf"):
        self.model = Model()
        self.ner = spacy.load(ner_model)

    def predict_labels(self, text):
        prediction = self.model.predict(text)
        print(prediction)
        return prediction

    def keyword_search(self, text, phrases):
        for phrase in phrases:
            if any(phrase.lower() in text.lower() for phrase in phrases):
                return True
        return False

    def determine_status(self, text):
        applied_phrases = [
            "we received your application", "we have received your application",
            "we look forward to reviewing your application", "We’ve received your application",
            "will be reviewed", "Your application has been received",
            "will review it shortly"
        ]

        reject_phrases = [
            "not to move forward", "We regret to inform you", "other candidates", "other applicants",
            "unable to offer you", "you were not selected", "unable to move forward",
            "we are pursuing other applicants",
        ]

        return self.predict_labels(text)
    
    def extract_company_name(self, text):
        company_name = "Unknown"
        nes = self.ner(text)
        org_names = [ent.text for ent in nes.ents if ent.label_ == "ORG"]
        if org_names:
            company_name = org_names[0]
        return company_name


class ApplicationTracker:
    def __init__(self, tracker_file):
        self.tracker_file = tracker_file

    def update_application_tracker(self, emails_data, email_processor):
        tracker_data = []
        try:
            with open(self.tracker_file, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    tracker_data.append(row)
        except FileNotFoundError:
            pass

        emails_data['Status'] = email_processor.determine_status(emails_data['text'].tolist())
        for _,email_data in emails_data.iterrows():
            if email_data['Status'] == "Irrelevant":
                continue
            company_name = email_processor.extract_company_name(email_data['text'])
            tracker_data.append({
                'Company Name' : company_name,
                'Email': email_data['From'],
                'Status': email_data['Status'],
            })

        tracker_data.sort(key=lambda x: (x['Status'] == "Rejected", x['Company Name']))

        with open(self.tracker_file, mode='w', newline='', encoding='utf-8') as file:
            fieldnames = ['Company Name', 'Status', 'Email']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for entry in tracker_data:
                writer.writerow(entry)
        print(f"{self.tracker_file} updated")


class EmailDataManager:
    def __init__(self, emails_csv_path, application_tracker_path):
        self.emails_csv_path = emails_csv_path
        self.application_tracker = ApplicationTracker(application_tracker_path)

    def read_processed_emails(self):
        try:
            df = pd.read_csv(self.emails_csv_path, encoding='utf-8')
            df['ParsedDate'] = pd.to_datetime(df['ParsedDate'], errors='coerce')
            sorted_df = df.sort_values(by='ParsedDate')
            return sorted_df
        except FileNotFoundError:
            # Return an empty DataFrame if the file does not exist
            return pd.DataFrame()


def main():
    emails_csv_path = 'processEmails/processed_emails.csv'
    application_tracker_path = 'applicationTracker.csv'
    email_processor = EmailProcessor()
    email_data_manager = EmailDataManager(emails_csv_path, application_tracker_path)

    emails_data = email_data_manager.read_processed_emails()
    email_data_manager.application_tracker.update_application_tracker(emails_data, email_processor)


if __name__ == "__main__":
    main()
