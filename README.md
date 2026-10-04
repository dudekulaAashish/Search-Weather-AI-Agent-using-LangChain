```powershell
conda create -n langagent python=3.11 -y
conda activate langagent
python -m pip install -r requirements.txt
python -m streamlit run app.py
```