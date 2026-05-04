import os

MODEL_DIR = os.getenv("SENTIMENT_MODEL_PATH", "src/model")

def load_and_split_csv(csv_path, test_size=0.2):
    from datasets import Dataset
    import pandas as pd
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(csv_path)
    df = normalize_training_dataframe(df)

    if test_size == 0:
        return Dataset.from_pandas(df, preserve_index=False), None

    train_df, test_df = train_test_split(
        df,
        test_size=test_size,
        stratify=df["label"],
        random_state=42,
    )
    return (
        Dataset.from_pandas(train_df, preserve_index=False),
        Dataset.from_pandas(test_df, preserve_index=False),
    )

def normalize_training_dataframe(df):
    required_columns = {"text", "label"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Training CSV missing required columns: {sorted(missing_columns)}")

    df = df[["text", "label"]].copy()
    df["text"] = df["text"].fillna("").astype(str).str.strip()
    df = df[df["text"] != ""]
    df = df.drop_duplicates(subset=["text"])

    label_map = {
        -1: 0,
        0: 1,
        1: 2,
        "-1": 0,
        "0": 1,
        "1": 2,
        "negative": 0,
        "neutral": 1,
        "positive": 2,
        "bearish": 0,
        "bullish": 2,
    }
    df["label"] = df["label"].map(lambda value: label_map.get(str(value).strip().lower(), label_map.get(value)))

    invalid_count = df["label"].isna().sum()
    if invalid_count:
        raise ValueError(f"Training CSV contains {invalid_count} rows with unsupported labels.")

    df["label"] = df["label"].astype(int)
    label_counts = df["label"].value_counts()
    if len(label_counts) < 2:
        raise ValueError("Training CSV must contain at least two sentiment classes.")
    if label_counts.min() < 2:
        raise ValueError("Each sentiment class must have at least two rows for stratified splitting.")

    return df

def compute_metrics(eval_pred):
    import numpy as np
    from sklearn.metrics import accuracy_score, f1_score

    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1": f1_score(labels, preds, average="weighted")
    }

def fine_tune_from_csv(csv_path, model_ckpt="ProsusAI/finbert"):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
    import torch

    if os.path.exists(MODEL_DIR):
        print(f"Model already exists at {MODEL_DIR}. Skipping training.")
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
        output_dir=MODEL_DIR,
        eval_strategy="epoch",
        save_strategy="epoch",
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=3,
        logging_dir=f"{MODEL_DIR}/logs",
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
    model.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)

def update_model_with_new_data(new_csv):
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
    import torch

    dataset, _ = load_and_split_csv(new_csv, test_size=0.0)  # All as train
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)

    def tokenize(batch):
        # Sanitize any NaNs or bad types
        texts = [str(t) if isinstance(t, str) else "" for t in batch["text"]]
        return tokenizer(texts, padding="max_length", truncation=True)

    dataset = dataset.map(tokenize, batched=True)

    training_args = TrainingArguments(
        output_dir=MODEL_DIR,
        eval_strategy="no",
        save_strategy="epoch",
        per_device_train_batch_size=16,
        num_train_epochs=1,
        logging_dir=f"{MODEL_DIR}/logs",
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
    model.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)

def upload_model_to_huggingface():
    from huggingface_hub import HfApi

    api = HfApi(token=os.getenv("HF_TOKEN"))
    api.upload_folder(
        folder_path=MODEL_DIR,
        repo_id="Zking136/StockTradingAI-Model",
        repo_type="model",
    )

def download_model_from_huggingface(repo_id="Zking136/StockTradingAI-Model"):
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=repo_id, local_dir=MODEL_DIR)

if __name__ == "__main__":
    # import torch
    # device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # print("Using device:", device)
    upload_model_to_huggingface()
