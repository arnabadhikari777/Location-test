# Location Test (Flask + SQLite)

## লোকাল চালানো
    python -m venv venv
    source venv/bin/activate        # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    python app.py
http://127.0.0.1:5000 (হোম) ও http://127.0.0.1:5000/admin (অ্যাডমিন)

## GitHub এ push
`.env` ও `*.db` `.gitignore` এ আছে, তাই push হবে না (এটাই ঠিক)।

    git init
    git add .
    git commit -m "Initial commit"
    git branch -M main
    git remote add origin https://github.com/USERNAME/REPO.git
    git push -u origin main

## PythonAnywhere এ হোস্ট
1. **Bash console** খুলে:
       git clone https://github.com/USERNAME/REPO.git location_test
       cd location_test
       mkvirtualenv --python=python3.12 locenv
       pip install -r requirements.txt
2. `.env` GitHub এ নেই, তাই সার্ভারে বানাও:
       cp .env.example .env
       nano .env     # SECRET_KEY, ADMIN_PASSWORD বসাও, COOKIE_SECURE=1, FLASK_DEBUG=0
3. **Web** ট্যাব → *Add a new web app* → *Manual configuration* → Python 3.12।
4. *Virtualenv* ঘরে দাও: `/home/yourusername/.virtualenvs/locenv`
5. *WSGI configuration file* খুলে সব মুছে `wsgi_pythonanywhere.py` এর কোড বসাও (path ঠিক করে)।
6. **Reload** চাপো। সাইট: `https://yourusername.pythonanywhere.com` (HTTPS আছে, তাই লোকেশন কাজ করবে)।

আপডেট করতে: কনসোলে `git pull` তারপর Web ট্যাবে Reload।
