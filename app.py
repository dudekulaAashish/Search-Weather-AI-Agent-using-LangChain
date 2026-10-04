import os
from pathlib import Path

import certifi
import requests
import streamlit as st
from dotenv import load_dotenv
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import ChatOpenAI

st.set_page_config(
    page_title="Agentic AI Assistant",
    page_icon="🤖",
    layout="wide",
)

os.environ["SSL_CERT_FILE"] = certifi.where()
project_dir = Path(__file__).resolve().parent
for env_file in (project_dir / ".env", project_dir / "research" / ".env"):
    if env_file.is_file():
        load_dotenv(dotenv_path=env_file, override=False)

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
TAVILY_API_KEY = (os.getenv("TAVILY_API_KEY") or "").strip()
WEATHERSTACK_API_KEY = (os.getenv("WEATHERSTACK_API_KEY") or "").strip()

st.markdown(
    """
    <style>
    .block-container { max-width: 900px; padding-top: 2.5rem; }
    .hero {
        padding: 1.5rem 1.75rem;
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 1rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(120deg, rgba(77, 124, 254, 0.13), rgba(36, 184, 166, 0.08));
    }
    .hero h1 { margin: 0; }
    .hero p { margin: 0.5rem 0 0; opacity: 0.78; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>🤖 Agentic AI Assistant</h1>
        <p>Ask a question to search the web, check current weather, or both.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("About")
    st.write("Your assistant can use web search and current weather data.")
    st.divider()
    st.caption("API key status")
    st.write(f"OpenAI: {'Ready' if OPENAI_API_KEY else 'Not configured'}")
    st.write(f"Tavily: {'Ready' if TAVILY_API_KEY else 'Not configured'}")
    st.write(f"WeatherStack: {'Ready' if WEATHERSTACK_API_KEY else 'Optional'}")
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

if not OPENAI_API_KEY or not TAVILY_API_KEY:
    missing = [
        name
        for name, value in (
            ("OPENAI_API_KEY", OPENAI_API_KEY),
            ("TAVILY_API_KEY", TAVILY_API_KEY),
        )
        if not value
    ]
    st.error(
        f"Add {', '.join(missing)} to the project .env file or set it in your "
        "environment, then restart the app."
    )
    st.stop()


@tool
def get_weather_data(city: str) -> str:
    """Fetch current weather information for a city."""
    if not WEATHERSTACK_API_KEY:
        raise ValueError(
            "Weather lookup needs a WEATHERSTACK_API_KEY in the project .env file."
        )

    response = requests.get(
        "https://api.weatherstack.com/current",
        params={"access_key": WEATHERSTACK_API_KEY, "query": city},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if "current" not in data:
        error = data.get("error", {}).get("info", "No current weather data returned.")
        raise ValueError(f"WeatherStack could not fetch weather for {city}: {error}")

    current = data["current"]
    description = current.get("weather_descriptions") or ["Unavailable"]
    return (
        f"City: {city}\n"
        f"Temperature: {current['temperature']}°C\n"
        f"Weather: {description[0]}\n"
        f"Humidity: {current['humidity']}%"
    )


@st.cache_resource
def get_agent_executor() -> AgentExecutor:
    tools = [
        TavilySearchResults(max_results=3),
        get_weather_data,
    ]
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        api_key=OPENAI_API_KEY,
    )
    prompt = hub.pull("hwchase17/react")
    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        handle_parsing_errors=True,
    )


if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.markdown("#### Try asking")
    suggestions = [
        "Find the latest AI news",
        "What is the weather in Mumbai?",
        "Search for a local event and check the weather there",
    ]
    suggestion_columns = st.columns(len(suggestions))
    selected_suggestion = None
    for column, suggestion in zip(suggestion_columns, suggestions):
        if column.button(suggestion, use_container_width=True):
            selected_suggestion = suggestion

    if selected_suggestion:
        submitted_prompt = selected_suggestion
    else:
        submitted_prompt = st.chat_input("Ask about news, places, or weather...")
else:
    submitted_prompt = st.chat_input("Ask a follow-up question...")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if submitted_prompt:
    st.session_state.messages.append(
        {"role": "user", "content": submitted_prompt}
    )
    with st.chat_message("user"):
        st.markdown(submitted_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching and preparing an answer..."):
            try:
                response = get_agent_executor().invoke({"input": submitted_prompt})
                answer = response["output"]
            except Exception as exc:
                answer = (
                    "I couldn't complete that request. Check that your API keys "
                    "are valid and that the search, weather, and model services "
                    "are reachable."
                )
                error_detail = str(exc)
                for secret in (
                    OPENAI_API_KEY,
                    TAVILY_API_KEY,
                    WEATHERSTACK_API_KEY,
                ):
                    if secret:
                        error_detail = error_detail.replace(secret, "[redacted]")
                st.error(f"{type(exc).__name__}: {error_detail}")
            st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
