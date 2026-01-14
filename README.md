# TikTok-Streak

## ✨ Features

- ⏰ Scheduled daily execution at 21:00 PM
- 👥 Supports multiple users from list
- 🔐 Cookie-based authentication (no password needed)
- 📝 Detailed logging to `tiktok_logs.txt`
- 🎭 Headless or visible browser mode
- 🔁 Automatic retry on failures


## 📋 Prerequisites

- Python 3.8 or higher
- Google Chrome browser installed
- TikTok account with active login cookies

## 🔧 Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Install ChromeDriver

The script uses Selenium with Chrome. Make sure Chrome is installed.

**Option A: Automatic (Recommended)**
```bash
pip install webdriver-manager
```

**Option B: Manual**
- Download ChromeDriver from: https://chromedriver.chromium.org/
- Place it in your PATH or same directory as script

## ⚙️ Configuration

### Export Your TikTok Cookies

1. Install Cookie-Editor extension:
   - Chrome: https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm
   
2. Login to TikTok in your browser

3. Click the Cookie-Editor extension icon

4. Click "Export" button (choose "JSON" format)

5. Save the exported cookies to `cookies.json` in the script directory

### 2. Add User List

Edit `list.txt` and add TikTok usernames (one per line):

```
friend1
user123
bestfriend
coolperson
```

**Note:** Use usernames WITHOUT the @ symbol

### 3. Adjust Settings (Optional)

Edit `tiktok_auto_forward.py` to customize:

```python
CAPTCHA_CHECK_ATTEMPTS    # Helping check Captcha 
SEND_TIME = "21:00"       # Daily execution time (24-hour format)
MAX_RETRIES = 3           # Retry attempts per operation
WAIT_TIMEOUT = 20         # Seconds to wait for elements
```

## 🚀 Usage

### Run Once (Test Mode)

```bash
python tiktok_auto_forward.py
```

Uncomment this line in the script to run immediately on start:
```python
# run_tiktok_forward()  # Remove the # to run on startup
```
