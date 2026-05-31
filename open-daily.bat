@echo off
cd /d "C:\Users\Lenovo\Desktop\ai-daily"
python main.py ai
for %%f in (output\*-ai.html) do set "LATEST=%%f"
start "" "%LATEST%"
