#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example script for sentiment classification using the CardiffNLP Twitter RoBERTa model.

This script assumes that the model and its associated configuration files (e.g., tokenizer,
config.json, pytorch_model.bin) are available in a local directory.
Model reference: https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest
"""
import warnings
import logging

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F

import os, openai

# env
openai.api_key = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# Disable future warnings
warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=UserWarning)
logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)

# Mapping from class indices to sentiment labels.
# For the CardiffNLP sentiment model, the typical mapping is:
# 0 -> Negative, 1 -> Neutral, 2 -> Positive.
LABEL_MAPPING = {0: "Negative", 1: "Neutral", 2: "Positive"}

# Specify the path to the local model directory.
model_dir = "/Users/vonthd/models/twitter-roberta-base-sentiment"  # Adjust the path as necessary.

tokenizer = AutoTokenizer.from_pretrained(model_dir)
model = AutoModelForSequenceClassification.from_pretrained(model_dir)

def predict_sentiment(texts, tokenizer, model, device):
    """
    Predict the sentiment of a list of texts using the provided model and tokenizer.

    Args:
        texts (list of str): List of input texts to classify.
        tokenizer: The HuggingFace tokenizer.
        model: The sentiment classification PyTorch model.
        device: The device to run inference on (CPU or CUDA).

    Returns:
        list of tuples: Each tuple contains (input text, predicted sentiment label, probability mapping).
    """
    # Tokenize the input texts (with padding and truncation).
    inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True)
    inputs = {key: tensor.to(device) for key, tensor in inputs.items()}
    
    # Place model on device and set to evaluation mode.
    model.to(device)
    model.eval()

    with torch.no_grad():
        outputs = model(**inputs)

    # Apply softmax to obtain probability distribution over sentiment classes.
    probs = F.softmax(outputs.logits, dim=-1).cpu().numpy()
    predictions = probs.argmax(axis=1)

    results = []
    for text, pred, prob_array in zip(texts, predictions, probs):
        label = LABEL_MAPPING.get(pred, f"Label-{pred}")
        # Create a mapping of sentiment to its corresponding probability.
        prob_mapping = {
            "Negative": prob_array[0],
            "Neutral": prob_array[1],
            "Positive": prob_array[2]
        }
        results.append((text, label, prob_mapping))
    return results


def _fix_sentence(context: str) -> str:
    """Call OpenAI chat completion and always return a non-None string."""
    messages = [
        {"role": "system",
         "content": "You are a helpful spell checker and grammar assistant. Provide the corrected sentence without any additional text."},
        {"role": "user", "content": f"This sentence has some spelling errors and grammatical errors::\n{context}"},
    ]
    try:
        resp = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0,
            max_tokens=1024
        )
        # Safely extract the assistant’s reply
        choice = resp.choices[0] if resp.choices else None
        text = choice.message.content if choice and choice.message.content else ""
        
        return text.strip()
    except Exception:
        # On API or parsing errors, return an empty string to avoid None
        return ""
    

if __name__ == "__main__":
    # Define some example texts for sentiment analysis.
    # texts = [
    #     "I absolutely love this product! It's amazing.",
    #     "This is the worst experience I've ever had.",
    #     "I'm not sure if I like it or not."
    # ]
    texts = [
        "'Misery' was the best movie I've seen since I was a small boy",
        "'Misery' was the bset moive I've seen snice I was a small boy",
        "'Misery' was the bset moive I've seen snice me were a small boy",
    ]

    # Determine whether to run on GPU or CPU.
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    for i, text in enumerate(texts):
        print(f"Original Text: {text}")

        # Fix the sentence using OpenAI's chat completion.
        fixed_text = _fix_sentence(text)
        print(f"Fixed Text: {fixed_text}")

        # Get sentiment predictions.
        results = predict_sentiment(fixed_text, tokenizer, model, device)

        # Display the results.
        print("\n")
        for text, label, prob_mapping in results:
            print(f"Text: {text}")
            print(f"Predicted Sentiment: {label}")
            for sentiment, probability in prob_mapping.items():
                print(f"  {sentiment}: {probability:.4f}")
            print("\n")

        print("\n")
