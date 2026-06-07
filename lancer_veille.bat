@echo off
cd /d "C:\Users\betmg\Documents\IA\VEILLE IA LOCAL"

"C:\Users\betmg\AppData\Local\Programs\Python\Python313\python.exe" script\collect.py
"C:\Users\betmg\AppData\Local\Programs\Python\Python313\python.exe" script\analyze.py
"C:\Users\betmg\AppData\Local\Programs\Python\Python313\python.exe" script\generate_dashboard.py

start "" "dashboard\index.html"

pause