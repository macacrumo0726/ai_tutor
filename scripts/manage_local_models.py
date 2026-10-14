#!/usr/bin/env python3
"""Check or explicitly pull the two lightweight local research models."""
from __future__ import annotations
import argparse
import shutil
import subprocess

MODELS=("qwen3:4b","phi4-mini:3.8b")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--pull",action="store_true",help="Download missing models (several GB).")
    args=parser.parse_args()
    if not shutil.which("ollama"):
        raise SystemExit("Ollama no está instalado. Instálelo desde https://ollama.com y vuelva a ejecutar.")
    listed=subprocess.run(["ollama","list"],check=True,text=True,capture_output=True).stdout
    for model in MODELS:
        available=model.split(":")[0] in listed
        print(f"{model}: {'disponible' if available else 'faltante'}")
        if args.pull and not available:
            subprocess.run(["ollama","pull",model],check=True)

if __name__=="__main__": main()
