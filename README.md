```powershell
conda create -n langagent python=3.11 -y
conda activate langagent
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The app provides a chat interface with example prompts and a sidebar showing
which API keys are configured. Add `OPENAI_API_KEY` and `TAVILY_API_KEY` to
`.env` to use the assistant. `WEATHERSTACK_API_KEY` is needed for weather
queries; the app also checks `research/.env` for these keys.