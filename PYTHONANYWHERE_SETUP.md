# PythonAnywhere সেটআপ

## ১. ফাইল আপলোড
প্রজেক্ট ফোল্ডারের (যেমন `/home/YOURNAME/My-weather-app/`) সব ফাইল নতুন ফাইল দিয়ে বদলান।
আপনার পুরোনো `.env` আর `weather.db` মুছবেন না — নতুন কোড পুরোনো ডেটাবেসের সাথেই চলে।

## ২. প্যাকেজ
Bash কনসোলে (আপনার virtualenv চালু রেখে):

    pip install -r requirements.txt

## ৩. `.env` ফাইল (প্রজেক্ট ফোল্ডারের ভেতরে)
`.env.example` কপি করে `.env` নাম দিন এবং সব মান বদলান:

- `OPENWEATHER_API_KEY` — OpenWeatherMap-এর key
- `FLASK_SECRET_KEY` — লম্বা এলোমেলো মান। বানাতে: `python -c "import secrets; print(secrets.token_hex(32))"`
- `ADMIN_USERNAME`, `ADMIN_PASSWORD` — কমপক্ষে ১০ অক্ষরের শক্ত পাসওয়ার্ড
- (ঐচ্ছিক) `DATABASE_PATH`, `VISITOR_RETENTION_DAYS`, `DISPLAY_TIMEZONE`

> PythonAnywhere-এ ওয়েব অ্যাপের জন্য আলাদা "Environment variables" বক্স নেই — `.env` ফাইলই ব্যবহার করুন।
> কোড `.env` ফাইলটা প্রজেক্ট ফোল্ডার থেকেই পড়ে, তাই কোন ফোল্ডার থেকে চালু হলো তাতে সমস্যা নেই।
> `FLASK_SECRET_KEY` না থাকলে বা প্লেসহোল্ডার থাকলে অ্যাপ ইচ্ছা করেই চালু হয় না (Error log-এ কারণ লেখা থাকবে)।

## ৪. WSGI ফাইল
Web ট্যাবের WSGI configuration file-এ:

    import sys
    path = "/home/YOURNAME/My-weather-app"
    if path not in sys.path:
        sys.path.insert(0, path)

    from weather import app as application

`app.run()` লাইভ সাইটে চালাবেন না।

## ৫. HTTPS
Web ট্যাবে **Force HTTPS** চালু করুন। ব্রাউজারের লোকেশন শুধু HTTPS-এ কাজ করে, আর অ্যাডমিন কুকিও Secure মোডে চলে।

## ৬. Reload
Web ট্যাবে সবুজ **Reload** বোতাম চাপুন।

## ব্যবহার
- সাইট: `https://YOURNAME.pythonanywhere.com/`
- অ্যাডমিন: `/admin` (লগইন `/admin/login`) — প্যানেল প্রতি ১০ সেকেন্ডে নিজে থেকে আপডেট হয়।
- ৫ বার ভুল পাসওয়ার্ড দিলে ১৫ মিনিট লগইন বন্ধ থাকে।
- সমস্যা হলে Web ট্যাবের **Error log** দেখুন।
