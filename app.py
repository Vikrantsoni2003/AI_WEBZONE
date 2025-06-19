from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import hashlib
import uuid
from datetime import datetime, timedelta
import os
import google.generativeai as genai
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Configure Gemini AI
GEMINI_API_KEY = "AIzaSyA8xuRRBRpkqdoFG6oNBvXaPs8QvjI5ths"
genai.configure(api_key=GEMINI_API_KEY)

# Database setup
def init_db():
    conn = sqlite3.connect('ai_tools.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'normal',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Favorites table
    c.execute('''
    CREATE TABLE IF NOT EXISTS favorites (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        category TEXT NOT NULL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Feedback table
    c.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        message TEXT NOT NULL,
        rating INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Chat history table
    c.execute('''
    CREATE TABLE IF NOT EXISTS chat_history (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        message TEXT NOT NULL,
        response TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Ad views table (for rewarded ads simulation)
    c.execute('''
    CREATE TABLE IF NOT EXISTS ad_views (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        tutorial_unlocked TEXT
    )
    ''')
    
    # Payments table
    c.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        plan_type TEXT NOT NULL,
        amount REAL NOT NULL,
        payment_method TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Helper functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    return stored_password == hash_password(provided_password)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_info(user_id):
    conn = sqlite3.connect('ai_tools.db')
    c = conn.cursor()
    c.execute("SELECT username, email, role FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return {'username': user[0], 'email': user[1], 'role': user[2]}
    return None

def get_user_favorites(user_id):
    conn = sqlite3.connect('ai_tools.db')
    c = conn.cursor()
    c.execute("SELECT tool_name, category FROM favorites WHERE user_id = ?", (user_id,))
    favorites = c.fetchall()
    conn.close()
    return favorites

def check_ad_viewed(user_id):
    """Check if user has viewed an ad in the last hour"""
    conn = sqlite3.connect('ai_tools.db')
    c = conn.cursor()
    one_hour_ago = datetime.now() - timedelta(hours=1)
    c.execute("SELECT COUNT(*) FROM ad_views WHERE user_id = ? AND viewed_at > ?", 
              (user_id, one_hour_ago.strftime('%Y-%m-%d %H:%M:%S')))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def get_gemini_response(message, user_context=""):
    """Get response from Gemini AI"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare context about AI tools
        tools_context = """
        You are an AI assistant helping users with AI tools. You have knowledge of 285+ AI tools across categories like:
        - Image tools (DALL-E, Midjourney, Remove.bg, etc.)
        - Video tools (Synthesia, Pictory, Runway, etc.)
        - Text tools (ChatGPT, Jasper, Copy.ai, etc.)
        - Business tools (Notion AI, Fireflies, etc.)
        - And many more categories including Marketing, Social Media, Education, Research, Productivity, Audio, Code, Data Science, Finance, Healthcare, and Legal.
        
        Provide helpful, accurate information about AI tools and their use cases.
        """
        
        full_prompt = f"{tools_context}\n\nUser context: {user_context}\n\nUser question: {message}"
        
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"

# Routes
@app.route('/')
def home():
    user_info = None
    if 'user_id' in session:
        user_info = get_user_info(session['user_id'])
    
    # Get some featured tools for homepage
    featured_tools = [
        ("ChatGPT", "https://chat.openai.com/", "Advanced conversational AI assistant", "Text"),
        ("DALL-E 3", "https://openai.com/dall-e-3", "Most advanced AI image generator from OpenAI", "Image"),
        ("Synthesia", "https://www.synthesia.io/", "AI video generation with realistic avatars", "Video"),
        ("Jasper", "https://www.jasper.ai/", "AI content creation platform for marketing", "Business"),
        ("Midjourney", "https://www.midjourney.com/", "High-quality AI art generation with unique styles", "Image"),
        ("Runway", "https://runwayml.com/", "AI video editing and generation suite", "Video")
    ]
    
    return render_template('home.html', user_info=user_info, featured_tools=featured_tools)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('auth.html', form_type='signup')
        
        conn = sqlite3.connect('ai_tools.db')
        c = conn.cursor()
        
        # Check if user exists
        c.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, email))
        if c.fetchone():
            flash('Username or email already exists!', 'error')
            conn.close()
            return render_template('auth.html', form_type='signup')
        
        # Create user
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(password)
        c.execute("INSERT INTO users (id, username, email, password) VALUES (?, ?, ?, ?)",
                 (user_id, username, email, hashed_password))
        conn.commit()
        conn.close()
        
        session['user_id'] = user_id
        flash('Account created successfully!', 'success')
        return redirect(url_for('home'))
    
    return render_template('auth.html', form_type='signup')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('ai_tools.db')
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ? OR email = ?", (username, username))
        user = c.fetchone()
        conn.close()
        
        if user and verify_password(user[1], password):
            session['user_id'] = user[0]
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('auth.html', form_type='login')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/tools')
def tools():
    from ai_tool_data import ai_tools
    
    user_info = None
    user_favorites = []
    if 'user_id' in session:
        user_info = get_user_info(session['user_id'])
        user_favorites = [fav[0] for fav in get_user_favorites(session['user_id'])]
    
    # Get search and filter parameters
    search_query = request.args.get('search', '').lower()
    category_filter = request.args.get('category', 'all')
    
    # Filter tools
    filtered_tools = []
    for category, tools_list in ai_tools.items():
        if category_filter == 'all' or category_filter == category.lower():
            for tool_name, tool_url, tool_description in tools_list:
                if not search_query or search_query in tool_name.lower() or search_query in tool_description.lower():
                    filtered_tools.append({
                        'name': tool_name,
                        'url': tool_url,
                        'description': tool_description,
                        'category': category,
                        'is_favorite': tool_name in user_favorites
                    })
    
    return render_template('tools.html', 
                         tools=filtered_tools, 
                         categories=list(ai_tools.keys()),
                         user_info=user_info,
                         search_query=request.args.get('search', ''),
                         category_filter=category_filter)

@app.route('/prompts')
def prompts():
    user_info = None
    if 'user_id' in session:
        user_info = get_user_info(session['user_id'])
    
    # AI Prompts organized by category
    prompt_categories = {
        "Content Creation": [
            "Write a compelling blog post about [topic] targeting [audience]",
            "Create 10 engaging social media captions for [product/service]",
            "Generate a product description for [product] highlighting its key benefits",
            "Write an email newsletter about [topic] with a clear call-to-action",
            "Create a script for a 60-second explainer video about [concept]",
            "Write a press release announcing [news/event]",
            "Generate creative headlines for [topic] that grab attention",
            "Create a content calendar for [brand] for the next month",
            "Write compelling ad copy for [product] targeting [demographic]",
            "Generate ideas for a podcast series about [industry/topic]"
        ],
        "Business & Marketing": [
            "Develop a marketing strategy for launching [product] to [target market]",
            "Create a SWOT analysis for [company/product]",
            "Write a professional email to [recipient] about [purpose]",
            "Generate ideas for improving customer retention in [industry]",
            "Create a project timeline for [project] with key milestones",
            "Write a business proposal for [service] targeting [client type]",
            "Develop a pricing strategy for [product/service]",
            "Create a competitive analysis of [industry] leaders",
            "Write a sales pitch for [product] addressing [pain point]",
            "Generate KPIs for measuring [business goal]"
        ],
        "Creative Writing": [
            "Write a short story beginning with 'The last person on Earth...'",
            "Create character descriptions for a [genre] story set in [setting]",
            "Generate plot ideas for a [genre] novel about [theme]",
            "Write dialogue between two characters discussing [topic]",
            "Create a poem about [subject] in [style] format",
            "Write the opening chapter of a mystery novel",
            "Create a compelling villain with complex motivations",
            "Write a love letter from [character] to [character]",
            "Generate world-building details for a fantasy realm",
            "Write a dramatic monologue for a theater performance"
        ],
        "Education & Learning": [
            "Explain [complex concept] in simple terms for a [grade level] student",
            "Create a study guide for [subject] covering [topics]",
            "Generate quiz questions about [topic] with multiple choice answers",
            "Write a lesson plan for teaching [skill] to [audience]",
            "Summarize the key points of [book/article/research paper]",
            "Create flashcards for memorizing [subject] vocabulary",
            "Design a hands-on activity to teach [concept]",
            "Write learning objectives for a course on [topic]",
            "Create an assessment rubric for [assignment type]",
            "Generate discussion questions for [reading/topic]"
        ],
        "Technical & Code": [
            "Write Python code to [specific task] with error handling",
            "Explain how [technology/framework] works and its use cases",
            "Debug this code and suggest improvements: [code snippet]",
            "Create documentation for [function/API] with examples",
            "Generate test cases for [feature/function] covering edge cases",
            "Write a technical specification for [feature/system]",
            "Create a database schema for [application type]",
            "Write SQL queries to [specific data task]",
            "Generate API endpoints for [application functionality]",
            "Create a deployment guide for [application/service]"
        ],
        "Personal Productivity": [
            "Create a daily routine for [goal] that fits a [lifestyle]",
            "Generate a meal plan for [dietary preference] for one week",
            "Write a professional resume summary for [job title] position",
            "Create a workout plan for [fitness goal] with [time constraint]",
            "Plan a [duration] trip to [destination] including activities and budget",
            "Design a morning routine for maximum productivity",
            "Create a time-blocking schedule for [work type]",
            "Generate habits to improve [life area]",
            "Write SMART goals for [personal/professional objective]",
            "Create a system for organizing [digital/physical space]"
        ]
    }
    
    return render_template('prompts.html', prompt_categories=prompt_categories, user_info=user_info)

@app.route('/tutorials')
def tutorials():
    user_info = None
    can_access = False
    
    if 'user_id' in session:
        user_info = get_user_info(session['user_id'])
        # Pro users can access directly, normal users need to watch ad
        if user_info and user_info.get('role') == 'pro' or check_ad_viewed(session['user_id']):
            can_access = True
    
    # Updated tutorials with working YouTube videos
    tutorials_data = [
        {
            'title': 'Complete ChatGPT Tutorial - From Beginner to Advanced',
            'description': 'Master ChatGPT with this comprehensive guide covering prompts, techniques, and advanced features',
            'video_id': 'JTxsNm9IdYU',
            'duration': '45:30'
        },
        {
            'title': 'AI Image Generation with Midjourney - Complete Guide',
            'description': 'Learn to create stunning AI art with Midjourney from basic prompts to advanced techniques',
            'video_id': 'SVcsDDABEkM',
            'duration': '32:15'
        },
        {
            'title': 'Building AI Workflows with Zapier and ChatGPT',
            'description': 'Automate your work by connecting AI tools with Zapier for maximum productivity',
            'video_id': 'T1A7cUbLM',
            'duration': '28:45'
        },
        {
            'title': 'AI Video Creation with Synthesia - Complete Tutorial',
            'description': 'Create professional AI videos with avatars using Synthesia platform',
            'video_id': 'JEXvXHigEyPYwQrX',
            'duration': '25:20'
        },
        {
            'title': 'Content Writing with AI - Jasper and Copy.ai',
            'description': 'Master AI-assisted content creation and copywriting for marketing',
            'video_id': 'wShG8rNRf-k',
            'duration': '38:10'
        },
        {
            'title': 'DALL-E 3 Complete Guide - AI Image Generation',
            'description': 'Learn to create amazing images with DALL-E 3 and advanced prompting techniques',
            'video_id': 'mvgKZ8XjqKE',
            'duration': '22:35'
        },
        {
            'title': 'AI Productivity Tools - Notion AI, Grammarly & More',
            'description': 'Boost your productivity with the best AI tools for writing and organization',
            'video_id': 'yR4hNBNS6yc',
            'duration': '35:50'
        },
        {
            'title': 'AI Music Generation - Complete Guide to Suno AI',
            'description': 'Create original music and songs using AI with Suno and other music AI tools',
            'video_id': 'v-YtYvMieo0',
            'duration': '29:15'
        },
        {
            'title': 'AI Voice Cloning with ElevenLabs - Tutorial',
            'description': 'Learn to clone voices and create realistic AI speech with ElevenLabs',
            'video_id': 'TQTlCHxyuu8',
            'duration': '18:40'
        },
        {
            'title': 'AI Code Assistant - GitHub Copilot Complete Guide',
            'description': 'Supercharge your coding with GitHub Copilot and AI programming assistants',
            'video_id': 'Fi3AJZZregI',
            'duration': '31:25'
        },
        {
            'title': 'AI Business Automation - Complete Workflow Setup',
            'description': 'Automate your entire business workflow using AI tools and integrations',
            'video_id': 'VYsVOBf0pR4',
            'duration': '42:10'
        },
        {
            'title': 'AI Research Tools - Elicit, Consensus & More',
            'description': 'Accelerate your research with AI-powered tools for academic and business research',
            'video_id': 'KGKCfjOF5nE',
            'duration': '26:30'
        },
        {
            'title': 'AI Social Media Marketing - Complete Strategy',
            'description': 'Create viral content and grow your social media using AI tools and strategies',
            'video_id': 'QsQyqcy7tZs',
            'duration': '33:45'
        },
        {
            'title': 'AI Data Analysis with ChatGPT and Claude',
            'description': 'Analyze data, create charts, and generate insights using AI assistants',
            'video_id': 'ua2HvQP6c_I',
            'duration': '27:20'
        },
        {
            'title': 'AI Email Marketing - Automation and Personalization',
            'description': 'Create personalized email campaigns and automate marketing with AI',
            'video_id': 'bGqpf4Y8Z2k',
            'duration': '24:55'
        },
        {
            'title': 'AI Design Tools - Canva AI, Adobe Firefly & More',
            'description': 'Create professional designs using AI-powered design tools and techniques',
            'video_id': 'Zb9hNG7VOG4',
            'duration': '30:15'
        },
        {
            'title': 'AI Customer Service - Chatbots and Automation',
            'description': 'Build AI-powered customer service systems and chatbots for your business',
            'video_id': 'rQdibOsL1ps',
            'duration': '36:40'
        },
        {
            'title': 'AI SEO and Content Optimization',
            'description': 'Optimize your content for search engines using AI SEO tools and strategies',
            'video_id': 'HSzcc7kJcfY',
            'duration': '28:25'
        },
        {
            'title': 'AI Translation and Language Tools',
            'description': 'Break language barriers with AI translation and multilingual content creation',
            'video_id': 'aR5N2Jl8k14',
            'duration': '21:10'
        },
        {
            'title': 'Future of AI - Trends and Predictions for 2024',
            'description': 'Explore upcoming AI trends and prepare for the future of artificial intelligence',
            'video_id': 'Yf4BwDwJ5Sg',
            'duration': '39:30'
        }
    ]
    
    return render_template('tutorials.html', 
                         tutorials=tutorials_data, 
                         user_info=user_info, 
                         can_access=can_access)

@app.route('/watch_ad')
@login_required
def watch_ad():
    user_info = get_user_info(session['user_id'])
    if user_info['role'] == 'pro':
        flash('Pro users have unlimited access!', 'info')
        return redirect(url_for('tutorials'))
    
    return render_template('ad.html', user_info=user_info)

@app.route('/ad_complete', methods=['POST'])
@login_required
def ad_complete():
    # Record ad view
    conn = sqlite3.connect('ai_tools.db')
    c = conn.cursor()
    ad_id = str(uuid.uuid4())
    c.execute("INSERT INTO ad_views (id, user_id, tutorial_unlocked) VALUES (?, ?, ?)",
             (ad_id, session['user_id'], 'tutorials'))
    conn.commit()
    conn.close()
    
    flash('Ad completed! You now have access to tutorials for 1 hour.', 'success')
    return redirect(url_for('tutorials'))

@app.route('/profile')
@login_required
def profile():
    user_info = get_user_info(session['user_id'])
    user_favorites = get_user_favorites(session['user_id'])
    
    # Get user stats
    conn = sqlite3.connect('ai_tools.db')
    c = conn.cursor()
    
    # Count favorites
    c.execute("SELECT COUNT(*) FROM favorites WHERE user_id = ?", (session['user_id'],))
    favorites_count = c.fetchone()[0]
    
    # Count feedback submissions
    c.execute("SELECT COUNT(*) FROM feedback WHERE user_id = ?", (session['user_id'],))
    feedback_count = c.fetchone()[0]
    
    # Count chat interactions
    c.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (session['user_id'],))
    chat_count = c.fetchone()[0]
    
    conn.close()
    
    stats = {
        'favorites': favorites_count,
        'feedback': feedback_count,
        'chats': chat_count
    }
    
    return render_template('profile.html', 
                         user_info=user_info, 
                         user_favorites=user_favorites,
                         stats=stats)

@app.route('/upgrade_to_pro')
@login_required
def upgrade_to_pro():
    user_info = get_user_info(session['user_id'])
    return render_template('upgrade.html', user_info=user_info)

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    plan_type = request.form['plan_type']
    payment_method = request.form['payment_method']
    
    # Set amount based on plan
    amounts = {
        'monthly': 49.00,
        'yearly': 399.00
    }
    
    amount = amounts.get(plan_type, 49.00)
    
    # Calculate expiry date
    if plan_type == 'monthly':
        expires_at = datetime.now() + timedelta(days=30)
    else:  # yearly
        expires_at = datetime.now() + timedelta(days=365)
    
    # Record payment (in real app, integrate with payment processor)
    conn = sqlite3.connect('ai_tools.db')
    c = conn.cursor()
    
    payment_id = str(uuid.uuid4())
    c.execute("""INSERT INTO payments 
                 (id, user_id, plan_type, amount, payment_method, status, expires_at) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
             (payment_id, session['user_id'], plan_type, amount, payment_method, 'completed', expires_at))
    
    # Update user role to pro
    c.execute("UPDATE users SET role = 'pro' WHERE id = ?", (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    flash(f'Payment successful! Welcome to Pro! Your {plan_type} subscription is now active.', 'success')
    return redirect(url_for('profile'))

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    user_info = None
    if 'user_id' in session:
        user_info = get_user_info(session['user_id'])
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        rating = request.form.get('rating', 5)
        
        conn = sqlite3.connect('ai_tools.db')
        c = conn.cursor()
        feedback_id = str(uuid.uuid4())
        user_id = session.get('user_id')
        
        c.execute("INSERT INTO feedback (id, user_id, name, email, message, rating) VALUES (?, ?, ?, ?, ?, ?)",
                 (feedback_id, user_id, name, email, message, rating))
        conn.commit()
        conn.close()
        
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('feedback'))
    
    return render_template('feedback.html', user_info=user_info)

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    user_info = None
    if 'user_id' in session:
        user_info = get_user_info(session['user_id'])
    
    chat_history = []
    if 'user_id' in session:
        conn = sqlite3.connect('ai_tools.db')
        c = conn.cursor()
        c.execute("SELECT message, response, created_at FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", 
                 (session['user_id'],))
        chat_history = c.fetchall()
        conn.close()
        chat_history.reverse()  # Show oldest first
    
    if request.method == 'POST':
        message = request.form['message']
        
        # Get AI response
        user_context = f"User: {user_info['username'] if user_info else 'Anonymous'}"
        response = get_gemini_response(message, user_context)
        
        # Save to database if user is logged in
        if 'user_id' in session:
            conn = sqlite3.connect('ai_tools.db')
            c = conn.cursor()
            chat_id = str(uuid.uuid4())
            c.execute("INSERT INTO chat_history (id, user_id, message, response) VALUES (?, ?, ?, ?)",
                     (chat_id, session['user_id'], message, response))
            conn.commit()
            conn.close()
        
        # Add to current chat history
        chat_history.append((message, response, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        return render_template('chat.html', user_info=user_info, chat_history=chat_history, 
                             latest_message=message, latest_response=response)
    
    return render_template('chat.html', user_info=user_info, chat_history=chat_history)

@app.route('/toggle_favorite', methods=['POST'])
@login_required
def toggle_favorite():
    tool_name = request.form['tool_name']
    category = request.form['category']
    
    conn = sqlite3.connect('ai_tools.db')
    c = conn.cursor()
    
    # Check if already favorite
    c.execute("SELECT id FROM favorites WHERE user_id = ? AND tool_name = ?", 
             (session['user_id'], tool_name))
    existing = c.fetchone()
    
    if existing:
        # Remove from favorites
        c.execute("DELETE FROM favorites WHERE id = ?", (existing[0],))
        action = 'removed'
    else:
        # Add to favorites
        fav_id = str(uuid.uuid4())
        c.execute("INSERT INTO favorites (id, user_id, tool_name, category) VALUES (?, ?, ?, ?)",
                 (fav_id, session['user_id'], tool_name, category))
        action = 'added'
    
    conn.commit()
    conn.close()
    
    flash(f'{tool_name} {action} {"to" if action == "added" else "from"} favorites!', 'success')
    return redirect(url_for('tools'))

if __name__ == '__main__':
    app.run(debug=True)