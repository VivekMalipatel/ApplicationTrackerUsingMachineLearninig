from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch

class Config:
    MAX_LEN = 512
    MODEL_PATH = "applicationTracker_DeBERTa_v3_base_finetuned"
    BATCH_SIZE = 128 #8 if 'xsmall' in MODEL_PATH else 4
    device = 'cuda:5' if torch.cuda.is_available() else torch.device("mps")

    hypothesis_class_label_dic = {
    "Applied": "The email is related to a job application that the recipient has submitted, for instance, a confirmation email received after applying for a job.",
    "Rejected": "The email is related to a rejection from a job application, indicating that the recipient was not selected for the job role or that the application will not be moving forward.",
    "Irrelevant": "The email is not related to job applications, such as applying, being rejected, or being accepted for a job role. It does not pertain to the status or process of job applications.",
    "Accepted": "The email is related to the acceptance of a job application, indicating that the recipient has not just applied but got selected or accepted for a job position or a job role following an application."
    }

    hypothesis_company_name_dic = {}
    hypothesis_class_lst = list(hypothesis_class_label_dic.values())

class Model:
    def __init__(self):
        
        self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_PATH, model_max_length = Config.MAX_LEN, truncation = True)
        self.model = AutoModelForSequenceClassification.from_pretrained(Config.MODEL_PATH)
        self.pipe_classifier = pipeline(
                                "zero-shot-classification",
                                model=self.model,  
                                tokenizer=self.tokenizer,
                                framework="pt",
                                device=Config.device,
                            )
        self.predict()
    
    def predict(self, text =["The Subject : ""Ext Confirmation On The Position Of Software Developer Internship At Interactive Brokers LLC."" - End of the Subject The email: ""Dear Shoaib Mohammed We are pleased to extend the following offer of employment to you on behalf of Interactive Brokers LLC You have been selected a the best candidate for the Software Developer Internship position Congratulations We believe that your knowledge skill and experience would be an ideal fit for our IT department team We hope you will enjoy your role and make significant contribution to the overall success of Interactive Brokers LLC Please take the time to review our offer It includes important detail about your compensation benefit and the term and condition of your anticipated employment with Interactive Brokers LLC We will need all form signed and returned a soon a possible We are very excited to start this journey together and can wait to have you join the team You are expected to contact Cindy Via Trillian IM platform a regard further briefing on the position and Training Best Regard Recruiting Team"" -end of the email. "], hypothesis_class_label_dic=Config.hypothesis_class_label_dic, hypothesis_class_lst=Config.hypothesis_class_lst):

        pipe_output = self.pipe_classifier(
                        text,
                        candidate_labels=hypothesis_class_lst,
                        hypothesis_template="{}",
                        multi_label=False,
                        batch_size=Config.BATCH_SIZE
                    )
        hypothesis_pred_true_probability = []
        hypothesis_pred_true = []
        for dic in pipe_output:
            hypothesis_pred_true_probability.append(dic["scores"][0])
            hypothesis_pred_true.append(dic["labels"][0])

        # map the long hypotheses to their corresponding short label names
        hypothesis_label_dic_inference_inverted = {value: key for key, value in hypothesis_class_label_dic.items()}
        label_pred = [hypothesis_label_dic_inference_inverted[hypo] for hypo in hypothesis_pred_true]
        print(label_pred)
        return label_pred
    
#Model()