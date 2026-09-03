#!/usr/bin/env python3
"""QLoRA/SFT entry point. Intended for a CUDA Linux training environment."""
from __future__ import annotations
import argparse

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--model",default="Qwen/Qwen3-8B"); parser.add_argument("--dataset",default="data/training/precalculus_sft.jsonl"); parser.add_argument("--output",default="data/artifacts/qwen3-precalculus-lora"); parser.add_argument("--epochs",type=float,default=2); args=parser.parse_args()
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM,AutoTokenizer,BitsAndBytesConfig
    from trl import SFTConfig,SFTTrainer
    import torch
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_compute_dtype=torch.bfloat16)
    model=AutoModelForCausalLM.from_pretrained(args.model,quantization_config=quant,device_map="auto",torch_dtype=torch.bfloat16)
    tokenizer=AutoTokenizer.from_pretrained(args.model)
    dataset=load_dataset("json",data_files=args.dataset,split="train").filter(lambda row:row["split"]=="train")
    config=SFTConfig(output_dir=args.output,num_train_epochs=args.epochs,learning_rate=1e-4,per_device_train_batch_size=1,gradient_accumulation_steps=16,bf16=True,logging_steps=10,save_strategy="epoch",report_to="none",assistant_only_loss=True)
    lora=LoraConfig(r=16,lora_alpha=32,lora_dropout=.05,bias="none",task_type="CAUSAL_LM",target_modules=["q_proj","k_proj","v_proj","o_proj"])
    trainer=SFTTrainer(model=model,args=config,train_dataset=dataset,processing_class=tokenizer,peft_config=lora)
    trainer.train(); trainer.save_model(args.output)
if __name__=="__main__": main()
