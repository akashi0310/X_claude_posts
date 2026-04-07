@echo off
cd /d C:\Users\ADMIN\Documents\X_claude_posts\claude_test
call venv\Scripts\activate
python main.py scrape --pw
python main.py index
