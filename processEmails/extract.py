import csv
import re
import os
import spacy
import joblib
from llm_inference import Model
from collections import Counter

class EmailProcessor:
    def __init__(self, model_path='model/classification/naive_bayes_model.joblib', nlp_model="en_core_web_trf"):
        self.model = Model()
        self.nlp = spacy.load(nlp_model)
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
        else:
            raise FileNotFoundError(f"Model file not found at {model_path}")

    def predict_label(self, text):
        text_lst = [text]*10
        prediction = self.model.predict(text_lst)
        counter = Counter(prediction)
        most_common_element, _ = counter.most_common(1)[0]
        return most_common_element

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

        if self.predict_label(text) == "Applied" :#or self.keyword_search(text, applied_phrases) or self.keyword_search(text, applied_phrases) :
            return "Applied"
        elif  self.predict_label(text) == "Rejected" :#or self.keyword_search(text, reject_phrases) or self.keyword_search(text, reject_phrases) :
            return "Rejected"
        elif  self.predict_label(text) == "Accepted" :#or self.keyword_search(text, reject_phrases) or self.keyword_search(text, reject_phrases) :
            return "Accepted"
        return "Irrelevant"

    def extract_company_role_name(self, email, body, subject):
        role = "Unknown"
        combined_text = subject + " " + body
        doc = self.nlp(combined_text)
        names_entities = [ent.text for ent in doc.ents if ent.label_ == "ORG"]

        match = re.match(r'(.+?)\s*<.*?>', email)
        if match:
            return match.group(1).strip(), role
        else:
            domain_match = re.search(r'(?<=@)[^>]+(?=\.)', email)
            if domain_match:
                return domain_match.group(0).capitalize(), role

        if len(names_entities) > 0:
            return names_entities[0], role
        return "Unknown", role


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

        for email_data in emails_data:
            status = email_processor.determine_status(email_data['text'])
            if status == "Irrelevant":
                continue
            company_name, role = email_processor.extract_company_role_name(email_data['From'], email_data['Body'], email_data['Subject'])
            company_name = company_name.strip()
            found = False
            '''
            for entry in tracker_data:
                if entry['Email'].lower() == email_data['From'].lower():
                    entry['Status'] = status  # Update existing entry status
                    found = True
                    break
            if not found:
            '''
            tracker_data.append({
                'Company Name': company_name,
                'Status': status,
                'Email': email_data['From']
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
            with open(self.emails_csv_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                return sorted([row for row in reader], key=lambda x: x['ParsedDate'])
        except FileNotFoundError:
            return []


def main():
    emails_csv_path = 'processEmails/processed_emails.csv'
    application_tracker_path = 'applicationTracker.csv'
    email_processor = EmailProcessor()
    email_data_manager = EmailDataManager(emails_csv_path, application_tracker_path)

    emails_data = email_data_manager.read_processed_emails()
    email_data_manager.application_tracker.update_application_tracker(emails_data, email_processor)


if __name__ == "__main__":
    main()
