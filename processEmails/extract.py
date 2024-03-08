import csv
import re
import os
import spacy
import joblib
import pandas as pd
from llm_inference import Config, Model
from collections import Counter

class EmailProcessor:
    def __init__(self, ner_model="en_core_web_trf"):
        self.model = Model()
        self.Config = Config()
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
        named_entities = [ent.text for ent in nes.ents if ent.label_ == "ORG"]
        if named_entities:
            named_entities_dict = {str(item): str(item) for item in named_entities}
            company_name = self.model.predict([text], named_entities_dict, named_entities)
        return company_name[0]


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
            print(company_name)
            tracker_data.append({
                'Company Name' : company_name,
                'Email': email_data['From'],
                'Status': email_data['Status'],
                'Status Updated' : email_data['Date']
            })
            
        tracker_data.sort(key=lambda x: (x['Status'] == "Rejected", x['Company Name']))
        
        with open(self.tracker_file, mode='w', newline='', encoding='utf-8') as file:
            fieldnames = ['Company Name', 'Status', 'Email', 'Status Updated']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for entry in tracker_data:
                writer.writerow(entry)
        print(f"{self.tracker_file} updated")


class EmailDataManager:
    def __init__(self, emails_csv_path, application_tracker_path):
        self.emails_csv_path = emails_csv_path
        self.application_tracker = ApplicationTracker(application_tracker_path)

    def read_emails(self):
        try:
            df = pd.read_csv(self.emails_csv_path, encoding='utf-8')
            df['ParsedDate'] = pd.to_datetime(df['ParsedDate'], errors='coerce')
            sorted_df = df.sort_values(by='ParsedDate')
            return sorted_df
        except FileNotFoundError:
            # Return an empty DataFrame if the file does not exist
            return pd.DataFrame()
    
    def flush_emails(self, emails_data, emails_csv_path, flush_path):
        emails_data = pd.DataFrame(emails_data)
        file_exists = os.path.isfile(flush_path) and os.path.getsize(flush_path) > 0

        all_emails = pd.read_csv(emails_csv_path)
        emails_to_flush = all_emails[all_emails['MessageID'].isin(emails_data['MessageID'])]
        emails_to_flush.to_csv(flush_path, mode='a', header=not file_exists, index=False)

        filtered_all_emails = all_emails[~all_emails['MessageID'].isin(emails_data['MessageID'])]
        filtered_all_emails.to_csv(emails_csv_path, index=False)

        print("Emails Flushed")


def main():
    emails_csv_path = 'processEmails/processed_emails.csv'
    application_tracker_path = 'applicationTracker.csv'
    flush_path = 'processEmails/flushed_processed_emails.csv'
    email_processor = EmailProcessor()
    email_data_manager = EmailDataManager(emails_csv_path, application_tracker_path)

    emails_data = email_data_manager.read_emails()
    #emails_data = emails_data.sample(frac=0.01)
    if emails_data.shape[0] == 0:
        print("No New Emails to Track")
    else :
        email_data_manager.application_tracker.update_application_tracker(emails_data, email_processor)
        email_data_manager.flush_emails(emails_data,emails_csv_path,flush_path)

if __name__ == "__main__":
    main()
