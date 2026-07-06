"""
╔══════════════════════════════════════════════════════════════════╗
║            AI-POWERED NUTRITION AGENT — Flask Backend            ║
║           IBM Watsonx.ai  ·  Granite Model  ·  Python            ║
╚══════════════════════════════════════════════════════════════════╝

AGENT_INSTRUCTIONS
──────────────────
Customize every aspect of the agent below without touching any other code.

  AGENT_TONE          : "friendly" | "professional" | "motivational"
  AGENT_DIET_FOCUS    : "balanced" | "vegetarian" | "vegan" | "keto" | "diabetic"
  AGENT_LANGUAGE_HINT : "English" | "Hinglish" (mix of Hindi + English)
  AGENT_INDIAN_FOCUS  : True  → prioritise Indian recipes, regional cuisines,
                                 festivals foods, local spices & ingredients
  AGENT_SAFETY_RULES  : list of hard rules the model must always respect
  AGENT_SYSTEM_PROMPT : full system-level instruction injected into every call

Edit the AGENT_CONFIG dict directly — changes take effect immediately on next request.
"""

import os
import json
import time
import logging
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for
)
from dotenv import load_dotenv

# ── IBM Watsonx.ai SDK ───────────────────────────────────────────
try:
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    WATSONX_AVAILABLE = True
except ImportError:
    WATSONX_AVAILABLE = False
    logging.warning("ibm-watsonx-ai not installed — running in DEMO mode.")

# ════════════════════════════════════════════════════════════════
#  AGENT INSTRUCTIONS  ← CUSTOMIZE HERE
# ════════════════════════════════════════════════════════════════
AGENT_CONFIG = {
    # ── Personality & Tone ──────────────────────────────────────
    "AGENT_TONE": "friendly",           # "friendly" | "professional" | "motivational"

    # ── Diet Specialization ─────────────────────────────────────
    "AGENT_DIET_FOCUS": "balanced",     # "balanced" | "vegetarian" | "vegan" | "keto" | "diabetic"

    # ── Language ────────────────────────────────────────────────
    "AGENT_LANGUAGE_HINT": "English",   # "English" | "Hinglish"

    # ── Indian Food Preference ──────────────────────────────────
    "AGENT_INDIAN_FOCUS": True,         # True → prioritise dals, sabzis, rotis, regional dishes

    # ── Safety Rules (always enforced) ──────────────────────────
    "AGENT_SAFETY_RULES": [
        "Never recommend extreme calorie deficits below 1200 kcal/day for adults.",
        "Always advise consulting a registered dietitian or doctor for medical conditions.",
        "Do not diagnose diseases or prescribe medicines.",
        "Flag any symptoms that require urgent medical attention.",
        "Provide age-appropriate advice when children or elderly are mentioned.",
    ],

    # ── Watsonx Model ───────────────────────────────────────────
    "MODEL_ID": "ibm/granite-13b-chat-v2",   # Granite chat model

    # ── Generation Parameters ───────────────────────────────────
    "GEN_PARAMS": {
        "max_new_tokens": 900,
        "min_new_tokens": 40,
        "temperature": 0.7,
        "top_p": 0.9,
        "repetition_penalty": 1.1,
    },
}

# Build the dynamic system prompt from AGENT_CONFIG
def _build_system_prompt() -> str:
    cfg = AGENT_CONFIG
    tone_map = {
        "friendly":       "warm, encouraging, and conversational",
        "professional":   "precise, evidence-based, and clinical",
        "motivational":   "energetic, positive, and goal-oriented",
    }
    diet_map = {
        "balanced":    "balanced omnivore",
        "vegetarian":  "lacto-vegetarian (no meat or fish)",
        "vegan":       "strictly plant-based vegan",
        "keto":        "ketogenic (high-fat, very low-carb)",
        "diabetic":    "diabetic-friendly (low GI, controlled carbs)",
    }
    safety_block = "\n".join(f"  • {r}" for r in cfg["AGENT_SAFETY_RULES"])
    indian_note  = (
        "Prefer Indian meals, regional cuisines (North/South/East/West India), "
        "traditional spices (turmeric, cumin, coriander), festive foods, and "
        "locally available ingredients wherever possible."
        if cfg["AGENT_INDIAN_FOCUS"] else ""
    )
    lang_note = (
        "You may sprinkle friendly Hindi words (Hinglish) naturally into responses."
        if cfg["AGENT_LANGUAGE_HINT"] == "Hinglish" else
        "Respond in clear, simple English."
    )

    return f"""You are NutriBot, an expert AI Nutrition Agent powered by IBM Watsonx.ai.

PERSONALITY: Be {tone_map.get(cfg['AGENT_TONE'], 'friendly')}.
DIET FOCUS: Specialise in {diet_map.get(cfg['AGENT_DIET_FOCUS'], 'balanced')} nutrition.
LANGUAGE: {lang_note}
{indian_note}

YOUR CAPABILITIES:
  • Personalised daily nutrition plans (calories, macros, micros)
  • Calorie analysis for meals and individual foods
  • Healthy meal suggestions for breakfast, lunch, dinner, and snacks
  • Family diet recommendations covering all age groups
  • BMI interpretation and weight management guidance
  • Hydration, sleep, and lifestyle tips linked to nutrition
  • Grocery shopping lists and budget-friendly meal ideas
  • Nutritional breakdown (proteins, fats, carbs, vitamins, minerals)
  • Festival / seasonal / occasion-based meal planning

SAFETY RULES (non-negotiable):
{safety_block}

RESPONSE FORMAT:
  - Use clear headings, bullet points, and emojis to enhance readability.
  - Include calorie counts and macro estimates whenever relevant.
  - End every response with one actionable "Quick Tip 💡" the user can try today.
  - Keep answers focused and under 400 words unless a detailed plan is requested.
"""

# ════════════════════════════════════════════════════════════════
#  Flask App Setup
# ════════════════════════════════════════════════════════════════
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════
#  Watsonx Client
# ════════════════════════════════════════════════════════════════
_watsonx_client = None

def get_watsonx_model() -> "ModelInference | None":
    """Return a cached ModelInference instance or None in demo mode."""
    global _watsonx_client
    if not WATSONX_AVAILABLE:
        return None
    if _watsonx_client:
        return _watsonx_client
    api_key    = os.getenv("IBM_API_KEY", "")
    project_id = os.getenv("IBM_PROJECT_ID", "")
    url        = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    if not api_key or not project_id:
        logger.warning("IBM_API_KEY / IBM_PROJECT_ID not set — demo mode active.")
        return None
    try:
        credentials = Credentials(api_key=api_key, url=url)
        client      = APIClient(credentials=credentials, project_id=project_id)
        params = {
            GenParams.MAX_NEW_TOKENS:      AGENT_CONFIG["GEN_PARAMS"]["max_new_tokens"],
            GenParams.MIN_NEW_TOKENS:      AGENT_CONFIG["GEN_PARAMS"]["min_new_tokens"],
            GenParams.TEMPERATURE:         AGENT_CONFIG["GEN_PARAMS"]["temperature"],
            GenParams.TOP_P:               AGENT_CONFIG["GEN_PARAMS"]["top_p"],
            GenParams.REPETITION_PENALTY:  AGENT_CONFIG["GEN_PARAMS"]["repetition_penalty"],
        }
        _watsonx_client = ModelInference(
            model_id   = AGENT_CONFIG["MODEL_ID"],
            api_client = client,
            params     = params,
        )
        logger.info("✅ Watsonx ModelInference initialised — model: %s", AGENT_CONFIG["MODEL_ID"])
    except Exception as exc:
        logger.error("❌ Watsonx init failed: %s", exc)
        _watsonx_client = None
    return _watsonx_client


def call_watsonx(user_message: str, conversation_history: list) -> str:
    """Call IBM Watsonx.ai and return the assistant reply as a string."""
    model = get_watsonx_model()
    system_prompt = _build_system_prompt()

    # Build the conversation context string
    history_text = ""
    for turn in conversation_history[-6:]:          # keep last 6 turns for context
        role  = turn.get("role", "user")
        text  = turn.get("content", "")
        history_text += f"{'User' if role == 'user' else 'NutriBot'}: {text}\n"

    full_prompt = (
        f"{system_prompt}\n\n"
        f"Conversation so far:\n{history_text}"
        f"User: {user_message}\n"
        f"NutriBot:"
    )

    if model is None:
        return _demo_response(user_message)

    try:
        result   = model.generate_text(prompt=full_prompt)
        response = result.strip() if isinstance(result, str) else str(result).strip()
        return response if response else "I'm sorry, I couldn't generate a response. Please try again."
    except Exception as exc:
        logger.error("Watsonx generation error: %s", exc)
        return f"⚠️ I encountered an issue: {exc}. Please try again in a moment."


def _demo_response(message: str) -> str:
    """Fallback demo response when Watsonx credentials are not configured."""
    msg_lower = message.lower()
    if any(k in msg_lower for k in ["bmi", "weight", "height"]):
        return (
            "## BMI & Weight Management 🏋️\n\n"
            "**BMI Categories:**\n"
            "- Underweight: < 18.5\n- Normal: 18.5–24.9\n"
            "- Overweight: 25–29.9\n- Obese: ≥ 30\n\n"
            "For personalised advice, ensure your IBM Watsonx credentials are configured in `.env`.\n\n"
            "**Quick Tip 💡** Aim for a gradual weight loss of 0.5–1 kg per week for sustainable results."
        )
    if any(k in msg_lower for k in ["breakfast", "morning"]):
        return (
            "## Healthy Breakfast Ideas 🌅\n\n"
            "**Indian Options:**\n"
            "- 🥣 Poha with peanuts & lemon — ~250 kcal\n"
            "- 🫓 Besan chilla with mint chutney — ~220 kcal\n"
            "- 🥛 Idli (3 pcs) + sambar — ~280 kcal\n\n"
            "**Quick Tip 💡** Always include a protein source at breakfast to stay full till lunch!"
        )
    if any(k in msg_lower for k in ["calorie", "calori", "kcal"]):
        return (
            "## Calorie Guide 🔥\n\n"
            "**Daily Calorie Needs (approx):**\n"
            "- Sedentary adult: 1800–2000 kcal\n"
            "- Active adult: 2200–2500 kcal\n"
            "- Weight loss goal: deficit of 300–500 kcal/day\n\n"
            "**Quick Tip 💡** Track your meals for just 3 days to spot hidden calorie sources!"
        )
    if any(k in msg_lower for k in ["plan", "diet", "week"]):
        return (
            "## 7-Day Balanced Meal Plan 📅\n\n"
            "**Day 1 Sample:**\n"
            "- 🌅 Breakfast: Oats upma + green tea (~300 kcal)\n"
            "- ☀️ Lunch: Dal rice + sabzi + salad (~550 kcal)\n"
            "- 🌙 Dinner: Roti + paneer bhurji + soup (~480 kcal)\n"
            "- 🍎 Snacks: Fruit + handful of nuts (~200 kcal)\n\n"
            "_Configure your IBM Watsonx credentials for a fully personalised plan._\n\n"
            "**Quick Tip 💡** Prep your vegetables on Sunday to make weekday cooking a breeze!"
        )
    return (
        "## NutriBot — Demo Mode 🤖\n\n"
        "Hello! I'm NutriBot, your AI-powered nutrition assistant.\n\n"
        "**I can help you with:**\n"
        "- 🥗 Personalised meal plans\n"
        "- 🔥 Calorie analysis\n"
        "- 🏋️ BMI & weight management\n"
        "- 👨‍👩‍👧 Family diet recommendations\n"
        "- 🍛 Indian & regional food suggestions\n\n"
        "⚙️ *Add your IBM Cloud API Key and Project ID in the `.env` file to unlock full AI capabilities.*\n\n"
        "**Quick Tip 💡** Start your day with a glass of warm water with lemon for a natural metabolism boost!"
    )


# ════════════════════════════════════════════════════════════════
#  Nutrition Helper Utilities
# ════════════════════════════════════════════════════════════════
def calculate_bmi(weight_kg: float, height_cm: float) -> dict:
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)
    if bmi < 18.5:
        category, color, advice = "Underweight", "#3b82f6", "Increase calorie intake with nutrient-dense foods."
    elif bmi < 25:
        category, color, advice = "Normal Weight", "#22c55e", "Maintain your healthy lifestyle — you're doing great!"
    elif bmi < 30:
        category, color, advice = "Overweight", "#f59e0b", "Reduce processed foods and increase physical activity."
    else:
        category, color, advice = "Obese", "#ef4444", "Consult a dietitian for a structured weight management plan."
    return {"bmi": bmi, "category": category, "color": color, "advice": advice}


def calculate_tdee(weight: float, height: float, age: int, gender: str, activity: str) -> dict:
    # Mifflin-St Jeor BMR
    if gender.lower() == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    multipliers = {
        "sedentary": 1.2, "light": 1.375,
        "moderate": 1.55, "active": 1.725, "very_active": 1.9,
    }
    tdee = round(bmr * multipliers.get(activity, 1.55))
    return {
        "bmr":         round(bmr),
        "tdee":        tdee,
        "weight_loss": tdee - 500,
        "weight_gain": tdee + 300,
        "protein_g":   round(weight * 1.6),
        "carbs_g":     round(tdee * 0.45 / 4),
        "fat_g":       round(tdee * 0.30 / 9),
    }


# ════════════════════════════════════════════════════════════════
#  Routes
# ════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    if "family_profiles" not in session:
        session["family_profiles"] = []
    if "chat_history" not in session:
        session["chat_history"] = []
    return render_template("index.html",
                           demo_mode=not bool(os.getenv("IBM_API_KEY", "").strip()))


@app.route("/api/chat", methods=["POST"])
def chat():
    data    = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    history = session.get("chat_history", [])
    history.append({"role": "user", "content": message, "time": datetime.now().strftime("%H:%M")})

    start   = time.time()
    reply   = call_watsonx(message, history)
    elapsed = round(time.time() - start, 2)

    history.append({"role": "assistant", "content": reply, "time": datetime.now().strftime("%H:%M")})
    session["chat_history"] = history[-40:]  # keep last 40 messages
    session.modified = True

    return jsonify({"reply": reply, "elapsed": elapsed, "model": AGENT_CONFIG["MODEL_ID"]})


@app.route("/api/bmi", methods=["POST"])
def bmi_endpoint():
    data = request.get_json(silent=True) or {}
    try:
        weight = float(data["weight"])
        height = float(data["height"])
        age    = int(data.get("age", 25))
        gender = data.get("gender", "male")
        activity = data.get("activity", "moderate")
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    bmi_result  = calculate_bmi(weight, height)
    tdee_result = calculate_tdee(weight, height, age, gender, activity)
    return jsonify({**bmi_result, **tdee_result})


@app.route("/api/meal-plan", methods=["POST"])
def meal_plan():
    data = request.get_json(silent=True) or {}
    calories  = data.get("calories", 2000)
    diet_type = data.get("diet_type", AGENT_CONFIG["AGENT_DIET_FOCUS"])
    days      = data.get("days", 7)
    allergies = data.get("allergies", [])
    goal      = data.get("goal", "maintain")

    allergy_note = f"Avoid: {', '.join(allergies)}." if allergies else ""
    prompt = (
        f"Create a {days}-day {diet_type} meal plan for {calories} kcal/day. "
        f"Goal: {goal} weight. {allergy_note} "
        "Include breakfast, lunch, dinner, and 2 snacks each day. "
        "Format as Day 1, Day 2 … with calorie counts per meal. "
        "Prioritise Indian meals."
    )
    reply = call_watsonx(prompt, [])
    return jsonify({"plan": reply, "calories": calories, "days": days})


@app.route("/api/analyze-meal", methods=["POST"])
def analyze_meal():
    data  = request.get_json(silent=True) or {}
    meal  = data.get("meal", "").strip()
    if not meal:
        return jsonify({"error": "Meal description required"}), 400
    prompt = (
        f"Analyse the nutritional content of this meal: '{meal}'. "
        "Provide: total calories, protein (g), carbohydrates (g), fat (g), fibre (g), "
        "key vitamins and minerals, and a health rating (1–10). "
        "If it's an Indian dish, mention its regional origin."
    )
    reply = call_watsonx(prompt, [])
    return jsonify({"analysis": reply, "meal": meal})


@app.route("/api/family-profile", methods=["POST"])
def save_family_profile():
    data    = request.get_json(silent=True) or {}
    members = data.get("members", [])
    if not members:
        return jsonify({"error": "No members provided"}), 400

    profiles = []
    for m in members:
        profiles.append({
            "name":     m.get("name", "Member"),
            "age":      m.get("age", 25),
            "gender":   m.get("gender", "male"),
            "weight":   m.get("weight", 65),
            "height":   m.get("height", 165),
            "activity": m.get("activity", "moderate"),
            "goal":     m.get("goal", "maintain"),
            "diet":     m.get("diet", AGENT_CONFIG["AGENT_DIET_FOCUS"]),
        })

    session["family_profiles"] = profiles
    session.modified = True

    # Generate family nutrition summary via Watsonx
    member_desc = "; ".join(
        f"{p['name']} (age {p['age']}, {p['gender']}, {p['activity']} activity, goal: {p['goal']})"
        for p in profiles
    )
    prompt = (
        f"Provide a family nutrition overview for: {member_desc}. "
        "Give each person's estimated daily calorie needs, key nutritional focus, "
        "and one personalised meal tip. Keep it concise and practical."
    )
    summary = call_watsonx(prompt, [])
    return jsonify({"profiles": profiles, "summary": summary})


@app.route("/api/family-profiles", methods=["GET"])
def get_family_profiles():
    return jsonify({"profiles": session.get("family_profiles", [])})


@app.route("/api/clear-chat", methods=["POST"])
def clear_chat():
    session["chat_history"] = []
    session.modified = True
    return jsonify({"status": "cleared"})


@app.route("/api/status", methods=["GET"])
def status():
    has_key     = bool(os.getenv("IBM_API_KEY", "").strip())
    has_project = bool(os.getenv("IBM_PROJECT_ID", "").strip())
    return jsonify({
        "status":          "ok",
        "demo_mode":       not (has_key and has_project),
        "watsonx_sdk":     WATSONX_AVAILABLE,
        "model":           AGENT_CONFIG["MODEL_ID"],
        "diet_focus":      AGENT_CONFIG["AGENT_DIET_FOCUS"],
        "tone":            AGENT_CONFIG["AGENT_TONE"],
        "indian_focus":    AGENT_CONFIG["AGENT_INDIAN_FOCUS"],
        "timestamp":       datetime.now().isoformat(),
    })


# ════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port  = int(os.getenv("APP_PORT", 5000))
    host  = os.getenv("APP_HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    logger.info("🚀 NutriBot starting on http://%s:%s  |  demo_mode=%s", host, port, not bool(os.getenv("IBM_API_KEY")))
    app.run(host=host, port=port, debug=debug)
