# Reflex Chat App

A user-friendly, highly customizable Python web app designed for chatting with Teagasc research papers.

# Getting Started

You'll need a .env file with the following env variables:

- RAGFLOW_API_KEY=						#Ragflow API key
- RAGFLOW_BASE_URL=						#Ragflow URL where API calls will be made, eg: http://hcux402.teagasc.net:9380
- AGENT_NAME=							#Name of Assistant
- REDIS_URL=redis://redis:6379			#Internal Docker URL pointing to redis
- API_URL=http://localhost:8001			#URL of the web socket

### 🧬 1. Clone the Repo

```bash
git clone https://github.com/Teagasc/Research-Paper-RAG.git
```

### 📦 2. Install Reflex

To get started with Reflex, you'll need:

- Python 3.7+
- Node.js 12.22.0+
- Pip dependencies: `reflex`, `reflex-chakra`, `python-dotenv`, `ragflow-sdk`

Install `pip` dependencies with the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 🚀 3. Run the application

Initialize and run the app:

```
reflex init
reflex run
```

# Features

- 100% Python-based, including the UI, using Reflex
- Create chat sessions
- Chat with specific research papers using the Documents menu
- See the source documents
- The application is fully customisable
    - See https://reflex.dev/docs/styling/overview for more details
- Responsive design for various devices

