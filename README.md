# NUS Course Selection Agent 🎓

[**English**](./README.md) | [**简体中文**](./README_zh.md)

An AI-powered academic assistant designed for NUS students. It provides personalized module recommendations, prerequisite validation, and preference-aware course planning using real-time data from NUSMods.

---

## ✨ Features
- **AI Intelligence**: Powered by Google Gemini 1.5 Pro or OpenRouter (NVIDIA Nemotron/Gemma).
- **Prerequisite Validator**: Recursive logic to check module eligibility based on taken modules.
- **Real-time Data**: Fetches latest module and timetable info via NUSMods API.
- **Streaming Response**: Real-time chat interface for fluid interaction.
- **Glassmorphic UI**: Premium, modern interface designed with Next.js and Tailwind CSS 4.

## 🛠️ Tech Stack
- **Backend**: FastAPI (Python 3.10+)
- **Frontend**: Next.js 15+, Tailwind CSS 4, Framer Motion
- **LLMs**: Google Gemini, OpenRouter (NVIDIA, Llama, etc.)

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- Node.js 18.x or higher
- An API Key from [Google AI Studio](https://aistudio.google.com/) or [OpenRouter](https://openrouter.ai/)

### 1. Backend Setup
```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:
```env
# Provider: 'gemini' or 'openrouter'
LLM_PROVIDER=gemini

# Keys (at least one)
GOOGLE_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=google/gemma-2-9b-it:free
```

Run the server:
```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The website will be available at [http://localhost:3000](http://localhost:3000).

---

## 📖 Usage
1.  **Set Profile**: Add your taken modules (e.g., `CS1010`, `CS1231S`) and career priorities in the left sidebar.
2.  **Test Connection**: Use the "Test Connection" button in the preferences to verify your LLM setup.
3.  **Chat**: Ask questions like "What AI courses should a CS freshman take?" or "Recommend some modules for a UI/UX career."

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.

---

> [!TIP]
> **Demo Mode**: If you haven't configured an API key yet, the agent will gracefully fall back to a simulation mode, allowing you to experience the interface immediately!
