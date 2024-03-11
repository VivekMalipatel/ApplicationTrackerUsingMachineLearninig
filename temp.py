import pandas as pd

data = pd.read_csv('processEmails/processed_emails.csv')

df = '\n'.join(data['text'])

with open('data.txt','w') as file:
    file.write(df[:20000])
