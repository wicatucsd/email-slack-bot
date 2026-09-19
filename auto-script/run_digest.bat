@echo off
:: change this to the directory of the repo on your computer
cd /d "C:\github projects\email-slack-bot"
python3 gmail_analyze.py
python3 generate_digest.py