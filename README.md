# 🚀 AI WebZone – Your Ultimate AI Tools Library with Prompts, Tutorials & AI Chatbot

**AI WebZone** is a full-stack AI-powered web application that offers a centralized platform for discovering top AI tools, learning how to use them, accessing powerful prompts, and chatting with an API-based AI assistant (powered by Google Generative AI). Built entirely with **Flask**, this project combines elegant UI with robust backend logic and smart AI integration.

---

## 🧠 Features

### 🛠️ AI Tools Library
- Curated collection of top AI tools
- Categorized by use-case: Image, Video, Text, Business, Education, etc.

### 💬 AI-Powered Chatbot
- API-based chatbot powered by **Google Generative AI**
- Chat interface with smart assistant for tool suggestions, info, and more

### 📚 Tutorials
- Step-by-step tutorials for using trending AI tools
- Learn and apply with real-world use cases

### ✨ Prompt Vault
- 50+ high-performing AI prompts
- Categorized and ready to copy

### 🔒 Secure Authentication
- Signup/Login with password hashing (SHA256 + salt)
- Session-based login system
- SQLite database for storing users and data

---

## 🧰 Tech Stack

- **Backend:** Flask, SQLite3, Google Generative AI API
- **Frontend:** HTML5, CSS3, Bootstrap, JavaScript
- **AI:** `google.generativeai` (Gemini API)
- **Security:** `hashlib`, `uuid`, `session`, salted password storage

---

## 📂 Project Structure

ai_webzone/
│
├── static/ # CSS, JS, Images
├── templates/ # HTML templates (Jinja2)
├── chatbot.py # Google Gemini-based chatbot logic
├── database.db # SQLite3 database file
├── app.py # Main Flask application
├── prompts.json # AI prompt collection
├── requirements.txt # Python dependencies
└── README.md # You're here!

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repo


git clone https://github.com/your-username/ai-webzone.git
cd ai-webzone
2️⃣ Install Requirements
bash
Copy
Edit
pip install -r requirements.txt
3️⃣ Add Your API Key
Create a .env file and add:

GOOGLE_API_KEY=your_google_generative_ai_key
Or set it in code directly using:

genai.configure(api_key="YOUR_API_KEY")
4️⃣ Run the App

python app.py
Visit: http://localhost:5000

📌 TODO / Future Enhancements
User profile page with bookmarks

Tool rating and reviews

Search and filter tools

Admin dashboard for uploading new tools/prompts

Ads & Pro Subscription logic

🛡️ License
This project is licensed under the MIT License.

🤝 Author
Developed by Vikrant SONI 
📍 India | 💻 MCA - AI & Data Science
🔗 GitHub: github.com/Vikrantsoni2003

---

### ✅ Extra Notes:

- `requirements.txt` should include:
Flask
google-generativeai
sqlite3 # usually built-in
uuid
python-dotenv
