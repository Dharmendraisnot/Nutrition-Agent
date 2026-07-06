# 🥗 NutriBot — AI-Powered Nutrition Agent

> **IBM Watsonx.ai · Granite Model · Flask · Bootstrap 5**

An intelligent, full-stack Nutrition Agent web application powered by IBM Watsonx.ai (Granite models). Features a conversational AI chat interface, nutrition dashboard, AI meal planner, BMI/TDEE calculator, family profile management, and a full Indian cuisine knowledge base — all in a beautiful dark-mode-enabled responsive UI.

---

## ✨ Features

| Feature | Description |
|---|---|
| 💬 **AI Chat** | Conversational nutrition assistant via IBM Granite model |
| 📊 **Dashboard** | Macro tracking, meal timing, micronutrient bars, hydration |
| 📅 **Meal Planner** | AI-generated 1–14 day meal plans with calorie targets |
| ❤️ **BMI Calculator** | BMR, TDEE, and personalised macro targets |
| 👨‍👩‍👧 **Family Profiles** | Multi-member family nutrition recommendations |
| 🍛 **Indian Cuisine** | Prioritises Indian regional foods and recipes |
| 🌙 **Dark Mode** | Full dark/light theme toggle |
| 📱 **Responsive** | Mobile-first Bootstrap 5 design |

---

## 📁 Project Structure

```
Nutrition Agent/
├── app.py                  ← Flask backend + AGENT_INSTRUCTIONS
├── requirements.txt        ← Python dependencies
├── .env.example            ← Environment variable template
├── .env                    ← Your secrets (never commit this!)
├── templates/
│   └── index.html          ← Main HTML template (Jinja2)
└── static/
    ├── css/
    │   └── style.css       ← Custom stylesheet
    └── js/
        └── app.js          ← Frontend JavaScript
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.9 or higher
- IBM Cloud account with Watsonx.ai access
- IBM Cloud API Key
- Watsonx.ai Project ID

### 2. Clone / Download

```bash
# If using git
git clone <your-repo-url>
cd "Nutrition Agent"
```

### 3. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

```bash
# Copy the example file
copy .env.example .env        # Windows
cp .env.example .env           # macOS/Linux

# Edit .env with your credentials
notepad .env                   # Windows
nano .env                      # macOS/Linux
```

Fill in your `.env`:

```ini
IBM_API_KEY=your_actual_ibm_cloud_api_key
IBM_PROJECT_ID=your_actual_watsonx_project_id
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
FLASK_SECRET_KEY=any-random-32-char-string-here
```

### 6. Run the App

```bash
python app.py
```

Open your browser at **http://localhost:5000** 🎉

---

## 🔑 Getting IBM Cloud Credentials

### IBM Cloud API Key
1. Go to [https://cloud.ibm.com/iam/apikeys](https://cloud.ibm.com/iam/apikeys)
2. Click **"Create an IBM Cloud API key"**
3. Copy the key and paste into `.env` as `IBM_API_KEY`

### Watsonx.ai Project ID
1. Go to [https://dataplatform.cloud.ibm.com/wx/home](https://dataplatform.cloud.ibm.com/wx/home)
2. Open or create a project
3. Click **"Manage" → "General"**
4. Copy the **Project ID** and paste into `.env` as `IBM_PROJECT_ID`

### Region URL
| Region | URL |
|---|---|
| US South | `https://us-south.ml.cloud.ibm.com` |
| EU (Frankfurt) | `https://eu-de.ml.cloud.ibm.com` |
| Asia Pacific (Tokyo) | `https://jp-tok.ml.cloud.ibm.com` |
| UK South | `https://eu-gb.ml.cloud.ibm.com` |

---

## ⚙️ Customizing the Agent (AGENT_INSTRUCTIONS)

Open `app.py` and find the `AGENT_CONFIG` dictionary (around line 45).

```python
AGENT_CONFIG = {
    # Change the personality
    "AGENT_TONE": "friendly",           # "friendly" | "professional" | "motivational"

    # Set diet specialization
    "AGENT_DIET_FOCUS": "vegetarian",   # "balanced" | "vegetarian" | "vegan" | "keto" | "diabetic"

    # Language preference
    "AGENT_LANGUAGE_HINT": "English",   # "English" | "Hinglish"

    # Prioritise Indian meals and recipes
    "AGENT_INDIAN_FOCUS": True,

    # Add or modify safety rules
    "AGENT_SAFETY_RULES": [
        "Never recommend extreme calorie deficits below 1200 kcal/day for adults.",
        "Always advise consulting a dietitian for medical conditions.",
        # Add your own rules here
    ],

    # Granite model selection
    "MODEL_ID": "ibm/granite-13b-chat-v2",

    # Fine-tune generation
    "GEN_PARAMS": {
        "max_new_tokens": 900,
        "temperature": 0.7,     # Lower = more factual, Higher = more creative
        "top_p": 0.9,
    },
}
```

Changes take effect immediately — no server restart needed mid-request.

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Main web application |
| `POST` | `/api/chat` | AI chat message |
| `POST` | `/api/bmi` | BMI + TDEE calculation |
| `POST` | `/api/meal-plan` | AI meal plan generation |
| `POST` | `/api/analyze-meal` | Nutritional analysis of a meal |
| `POST` | `/api/family-profile` | Save family profiles + get summary |
| `GET` | `/api/family-profiles` | Retrieve saved family profiles |
| `POST` | `/api/clear-chat` | Clear conversation history |
| `GET` | `/api/status` | App + Watsonx status check |

### Example: Chat API

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a 7-day vegetarian meal plan for 1800 calories"}'
```

---

## ☁️ Deployment

### Option 1: IBM Cloud Code Engine

```bash
# Build container
docker build -t nutribot .

# Push to IBM Container Registry
ibmcloud cr login
docker tag nutribot us.icr.io/<namespace>/nutribot:latest
docker push us.icr.io/<namespace>/nutribot:latest

# Deploy to Code Engine
ibmcloud ce app create --name nutribot \
  --image us.icr.io/<namespace>/nutribot:latest \
  --env IBM_API_KEY=<key> \
  --env IBM_PROJECT_ID=<id>
```

### Option 2: Heroku

```bash
# Add Procfile
echo "web: gunicorn app:app" > Procfile

heroku create nutribot-app
heroku config:set IBM_API_KEY=your_key
heroku config:set IBM_PROJECT_ID=your_project_id
heroku config:set FLASK_SECRET_KEY=your_secret
git push heroku main
```

### Option 3: Render / Railway

Set the following environment variables in the platform dashboard:
- `IBM_API_KEY`
- `IBM_PROJECT_ID`
- `IBM_WATSONX_URL`
- `FLASK_SECRET_KEY`

Start command: `gunicorn app:app`

### Option 4: Docker

```dockerfile
# Dockerfile (create this file)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

```bash
docker build -t nutribot .
docker run -p 5000:5000 --env-file .env nutribot
```

---

## 🧪 Demo Mode

If IBM credentials are not configured, the app runs in **Demo Mode** automatically:
- Pre-written intelligent responses for common nutrition queries
- All UI features work normally (BMI calculator, dashboard, etc.)
- A yellow banner alerts the user that AI is not connected
- Perfect for development, testing, and UI demos

---

## 🛡️ Security Notes

- Never commit `.env` to version control
- `.env` is listed in `.gitignore` automatically
- API keys are loaded at runtime from environment variables only
- Sessions are server-side with a secret key
- No user data is stored persistently (session-based only)

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `flask` | 3.0.3 | Web framework |
| `flask-session` | 0.8.0 | Server-side sessions |
| `python-dotenv` | 1.0.1 | .env file loading |
| `ibm-watsonx-ai` | 1.1.2 | IBM Watsonx.ai SDK |
| `requests` | 2.32.3 | HTTP client |
| `gunicorn` | 22.0.0 | Production WSGI server |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and test thoroughly
4. Commit: `git commit -m "Add your feature"`
5. Push and create a Pull Request

---

## 📄 License

MIT License — Free to use, modify, and distribute.

---

<p align="center">Made with ❤️ · Powered by IBM Watsonx.ai + Granite · Flask + Bootstrap 5</p>
