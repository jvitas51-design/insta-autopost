import subprocess; print(subprocess.run(['python3','app/catalog.py','logs/probe'],capture_output=True,text=True))
