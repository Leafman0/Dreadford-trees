python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --onefile --name Ishtar --add-data "ishtar;ishtar" app.py
