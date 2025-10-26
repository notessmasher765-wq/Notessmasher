@echo off
call venv\Scripts\activate
python app.py
pause

cd "C:\Study Resources"

git add . && git commit -m "Your descriptive message about changes" && git push origin main
