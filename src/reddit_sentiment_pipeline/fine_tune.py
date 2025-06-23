from datasets import Dataset
import os

def load_and_split_csv(csv_path, test_size=0.2):
    import pandas as pd
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(csv_path)
    # df = df.rename(columns={"clean_comment": "text", "category": "label"}) #adjust column names if necessary
    label_map = {-1: 0, 0: 1, 1: 2}
    df["label"] = df["label"].map(label_map)
    train_df, test_df = train_test_split(df, test_size=test_size, stratify=df["label"])
    return Dataset.from_pandas(train_df), Dataset.from_pandas(test_df)

def compute_metrics(eval_pred):
    import numpy as np
    from sklearn.metrics import accuracy_score, f1_score

    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1": f1_score(labels, preds, average="weighted")
    }

def fine_tune_from_csv(csv_path, model_ckpt="ProsusAI/finbert", output_dir="./model"):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
    import torch

    if os.path.exists(output_dir):
        print(f"Model already exists at {output_dir}. Skipping training.")
        return

    dataset_train, dataset_test = load_and_split_csv(csv_path)
    tokenizer = AutoTokenizer.from_pretrained(model_ckpt)
    
    def tokenize(batch):
        # Sanitize any NaNs or bad types
        texts = [str(t) if isinstance(t, str) else "" for t in batch["text"]]
        return tokenizer(texts, padding="max_length", truncation=True)

    dataset_train = dataset_train.map(tokenize, batched=True)
    dataset_test = dataset_test.map(tokenize, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(model_ckpt, num_labels=3)

    training_args = TrainingArguments(
        output_dir=output_dir,
        eval_strategy="epoch",
        save_strategy="epoch",
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=3,
        logging_dir=f"{output_dir}/logs",
        load_best_model_at_end=True,
        fp16=True if torch.cuda.is_available() else False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset_train,
        eval_dataset=dataset_test,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics
    )

    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

def update_model_with_new_data(new_csv, model_dir="./model"):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
    import torch

    dataset, _ = load_and_split_csv(new_csv, test_size=0.0)  # All as train
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)

    def tokenize(batch):
        # Sanitize any NaNs or bad types
        texts = [str(t) if isinstance(t, str) else "" for t in batch["text"]]
        return tokenizer(texts, padding="max_length", truncation=True)

    dataset = dataset.map(tokenize, batched=True)

    training_args = TrainingArguments(
        output_dir=model_dir,
        eval_strategy="no",
        save_strategy="epoch",
        per_device_train_batch_size=16,
        num_train_epochs=1,
        logging_dir=f"{model_dir}/logs",
        load_best_model_at_end=False,
        fp16=True if torch.cuda.is_available() else False
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer
    )

    trainer.train()
    model.save_pretrained(model_dir)
    tokenizer.save_pretrained(model_dir)

def upload_model_to_huggingface():
    from huggingface_hub import HfApi

    api = HfApi(token=os.getenv("HF_TOKEN"))
    api.upload_folder(
        folder_path="src\\model",
        repo_id="Zking136/StockTradingAI-Model",
        repo_type="model",
    )

def download_model_from_huggingface(repo_id="Zking136/StockTradingAI-Model", local_dir="./model"):
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=repo_id, local_dir=local_dir)

if __name__ == "__main__":
    # import torch
    # device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # print("Using device:", device)
    upload_model_to_huggingface()
