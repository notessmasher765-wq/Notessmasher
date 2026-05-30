@echo off
call venv\Scripts\activate
python app.py
pause

cd "C:\Study Resources"

git add . && git commit -m ""FIXING LOGIN AND REGISTER " && git push origin main


flask db migrate -m "FIXING LOGIN AND REGISTER"
flask db upgrade

git add requirements.txt
git commit -m "fix postgres driver"
git push origin main