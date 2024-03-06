from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch

class Config:
    MAX_LEN = 512
    MODEL_PATH = "/Users/vivekmalipatel/Downloads/llms/myModels/applicationTracker_DeBERTa_v3_large_finetuned"
    BATCH_SIZE = 4
    device = 'cuda' if torch.cuda.is_available() else torch.device("mps")

    hypothesis_label_dic = {
    "Applied": "The email is related to a job application that the recipient has submitted, for instance, a confirmation email received after applying for a job.",
    "Rejected": "The email is related to a rejection from a job application, indicating that the recipient was not selected for the job role or that the application will not be moving forward.",
    "Irrelevant": "The email is not related to job applications, such as applying, being rejected, or being accepted for a job role. It does not pertain to the status or process of job applications.",
    "Accepted": "The email is related to the acceptance of a job application, indicating that the recipient has been selected or considered for a job role following an application."
    }

class Model:
    def __init__(self):
        
        self.tokenizer = AutoTokenizer.from_pretrained(Config.MODEL_PATH, model_max_length = Config.MAX_LEN, truncation = True)
        self.model = AutoModelForSequenceClassification.from_pretrained(Config.MODEL_PATH)
        self.hypothesis_lst = list(Config.hypothesis_label_dic.values())

        self.pipe_classifier = pipeline(
                                "zero-shot-classification",
                                model=self.model,  
                                tokenizer=self.tokenizer,
                                framework="pt",
                                device=Config.device,
                            )
    
    def predict(self, text):
        pipe_output = self.pipe_classifier(
                        text,
                        candidate_labels=self.hypothesis_lst,
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
        hypothesis_label_dic_inference_inverted = {value: key for key, value in Config.hypothesis_label_dic.items()}
        label_pred = [hypothesis_label_dic_inference_inverted[hypo] for hypo in hypothesis_pred_true]
        return label_pred[0]