# -*- coding: utf-8 -*-
"""llama_recommendations.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1GTrBEUNY8fu_HbmIAcgxfiM8w--Sxlka
"""

model_name = "unsloth/llama-3-8b-Instruct-bnb-4bit"
model_alias = "llama3-8b"

from unsloth import FastLanguageModel
from datasets import load_dataset
from tqdm import tqdm
import csv
from pathlib import Path

WORK_DIR = Path(f"/vol/bitbucket/kza23/finetuning/{model_alias}")
WORK_DIR.mkdir(exist_ok=True)

max_seq_length = 20  # Choose any! We auto support RoPE Scaling internally!
dtype = (
    None  # None for auto detection. Float16 for Tesla T4, V100, Bfloat16 for Ampere+
)
load_in_4bit = True  # Use 4bit quantization to reduce memory usage. Can be False.

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=max_seq_length,
    dtype=dtype,
    load_in_4bit=load_in_4bit,
)

FastLanguageModel.for_inference(model)

test_dataset = load_dataset(
    "msc-smart-contract-audition/audits-with-reasons", split="test"
)

test_dataset

query_template = """
<|begin_of_text|><|start_header_id|>system<|end_header_id|>
Below is some solidity code and a description of a vulnerability that the code contains.

Explain how to mitigate or fix the vulnerability.
<|start_header_id|>user<|end_header_id|>
Codeblocks:
{}<|eot_id|>

Vulnerability:
{}<|eot_id|>

<|start_header_id|>assistant<|end_header_id|>
Solution:
"""

df_test = test_dataset.to_pandas()
df_test = df_test[df_test["description"].notnull()]
queries = df_test.apply(
    lambda row: query_template.format(
        row["code"].replace("\\n", "\n"), row["description"].replace("\\n", "\n")
    ),
    axis=1,
)

with open(WORK_DIR / "recommendations.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "output", "real"])

    for idx, (query, real) in tqdm(
        enumerate(zip(queries, test_dataset["recommendation"])), total=len(queries)
    ):
        inputs = tokenizer(query, return_tensors="pt", truncation=True).to("cuda")
        output_tokens = model.generate(
            **inputs, max_new_tokens=512, pad_token_id=tokenizer.pad_token_id
        )
        decoded_output = tokenizer.decode(
            output_tokens[0],
            skip_special_tokens=True,
            pad_token_id=tokenizer.pad_token_id,
        )
        recommendation = (
            decoded_output.split("Solution:\n")[1].strip().replace("\n", "\\n")
        )
        writer.writerow([idx, recommendation, real])