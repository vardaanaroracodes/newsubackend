# News Agent Service

## Overview

This project is a **Conversational AI-powered News Aggregation System** built using **Flask**, **LangChain**, and **Google Gemini API**. It enables users to **ask questions about recent news** and receive **summarized responses** along with relevant news articles.

##  Features

- **Conversational AI**: Uses **Gemini** to understand user queries and generate responses.
- **Real-time News Fetching**: Fetches news articles using **Serper API**.
- **Summarization**: Uses Gemini to summarize news articles.
- **Memory Storage**: Retains conversation history for context-aware responses.
- **Secure API Authentication**: Uses API keys for server-to-server security.

## Tech Stack

- **Frontend**: Next.js (Clerk for authentication)
- **Backend**: Flask (Blueprints for modular routing)
- **LLM**: Google Gemini via LangChain
- **News Fetching**: Serper API
- **Memory & Workflow Orchestration**: LangChain Agents & Tools

---
![System Diagram](assets/news-agent-diagram.png)

##  API Endpoints

###  `/news/ask` (POST)

**Purpose**: Takes a user query, retrieves relevant news articles, and returns an AI-generated summary.

📌Request:

```json
POST /news/ask
Headers: { "API_AUTH_KEY": "your-secret-key" }
Body:
{
  "query": "What are the latest AI advancements?"
}
```

 **Response:**

```json
{
  "success": true,
  "response": "AI is making progress in deep learning...",
  "sources": [
    { "title": "New AI Model", "link": "https://example.com", "source": "TechCrunch" }
  ]
}
```

###  `/news/clear` (POST)

**Purpose**: Clears the conversation history.

 **Request:**

```json
POST /news/clear
Headers: { "API_AUTH_KEY": "your-secret-key" }
```

 **Response:**

```json
{
  "success": true,
  "message": "Conversation history cleared"
}
```

###  `/news/history` (GET)

**Purpose**: Retrieves stored conversation history.

Request:

```json
GET /news/history
Headers: { "API_AUTH_KEY": "your-secret-key" }
```

 **Response:**

```json
{
  "success": true,
  "history": [
    { "role": "user", "content": "Tell me about AI" },
    { "role": "ai", "content": "AI is progressing rapidly in NLP..." }
  ]
}
```

---

## How It Works

1️⃣ **User submits a prompt** via the frontend. 2️⃣ **Backend authenticates the request** (checks API key & JWT from Clerk). 3️⃣ **AI extracts keywords** from the query (using Gemini). 4️⃣ **NewsAgentService fetches relevant articles** via Serper API. 5️⃣ **AI summarizes** the news articles and generates a response. 6️⃣ **Response is sent back** to the frontend. 7️⃣ **Conversation history is stored** (optional).

---

##  LangChain's Role

LangChain plays a vital role in: ✔ **Managing AI decision-making** (ReAct agents) ✔ **Integrating third-party APIs** (Google Gemini, Serper API) ✔ **Handling multi-step workflows** (Keyword Extraction → News Fetching → Summarization) ✔ **Retaining memory** (Conversation context for follow-ups) ✔ **Ensuring structured outputs** (Standardized JSON responses) ✔ **Automating retries and error handling** (Ensuring stability)

---

##  Installation & Setup

### **Clone the Repository**

```bash
git clone https://github.com/your-username/news-agent-service.git
cd news-agent-service
```

### \*\* Set Up Virtual Environment\*\*

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### \*\* Install Dependencies\*\*

```bash
pip install -r requirements.txt
```

### **Set Up Environment Variables**

Create a `.env` file in the root directory:

```bash
GOOGLE_API_KEY=your-google-api-key
SERPER_API_KEY=your-serper-api-key
API_AUTH_KEY=your-secret-auth-key
```

### ** Run the Flask App**

```bash
flask run
```

The API will be available at `http://127.0.0.1:5000/news`

---

##
---

## Security Considerations

✔ **API Key Authentication**: Protects the backend from unauthorized requests. ✔ **Rate Limiting**: (Recommended) Prevent abuse with Flask-Limiter. ✔ **CORS Policy**: Restrict frontend domains from accessing unauthorized resources. ✔ **Error Handling & Logging**: Logs all exceptions for debugging. ✔ **Sensitive Data Storage**: API keys are stored in `.env`, never hardcoded.

---

## License

This project is **MIT Licensed**. You are free to use, modify, and distribute it with attribution.

---

##  Contributing

1. **Fork the repo** and create a new branch.
2. **Make improvements & bug fixes.**
3. **Submit a Pull Request.**

For discussions, **open an issue** or reach out via **email**.



