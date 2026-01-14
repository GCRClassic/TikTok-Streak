#!/usr/bin/env python3

import json
import time
import random
import logging
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import List, Dict
import schedule

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException
)


# ============================================================================
# CONFIGURATION
# ============================================================================

SEND_TIME = "21:00"  # Daily execution time (24-hour format: HH:MM)
COOKIES_FILE = "cookies.json"
USERS_FILE = "list.txt"
LOG_FILE = "tiktok_logs.txt"

STREAK_MESSAGES = [
    "text 1",
    "text 2",
    "text 3",
]

MAX_RETRIES = 3
WAIT_TIMEOUT = 20
TYPING_DELAY_MIN = 0.05
TYPING_DELAY_MAX = 0.15
CAPTCHA_CHECK_ATTEMPTS = 3


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


# ============================================================================
# FILE OPERATIONS
# ============================================================================

def load_cookies() -> List[Dict]:
    try:
        with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        logger.info(f"✓ Loaded {len(cookies)} cookies from {COOKIES_FILE}")
        return cookies
    except FileNotFoundError:
        logger.error(f"✗ Cookie file not found: {COOKIES_FILE}")
        raise
    except json.JSONDecodeError:
        logger.error(f"✗ Invalid JSON in {COOKIES_FILE}")
        raise


def load_users() -> List[str]:
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = [line.strip().lstrip('@') for line in f if line.strip() and not line.startswith('#')]
        logger.info(f"✓ Loaded {len(users)} users from {USERS_FILE}")
        return users
    except FileNotFoundError:
        logger.error(f"✗ User file not found: {USERS_FILE}")
        raise


def log_activity(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {message}"
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')
    
    if level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)


# ============================================================================
# BROWSER SETUP
# ============================================================================

def setup_driver() -> webdriver.Chrome:
    options = Options()
    
    logger.info("Setting up Chrome driver...")
    
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
        '''
    })
    
    logger.info("✓ Chrome driver initialized")
    return driver


def load_cookies_to_driver(driver: webdriver.Chrome, cookies: List[Dict]):
    driver.get("https://www.tiktok.com")
    time.sleep(2)
    
    for cookie in cookies:
        try:
            cookie_dict = {
                'name': cookie.get('name'),
                'value': cookie.get('value'),
                'domain': cookie.get('domain', '.tiktok.com'),
            }
            
            if 'path' in cookie:
                cookie_dict['path'] = cookie['path']
            if 'expirationDate' in cookie:
                cookie_dict['expiry'] = int(cookie['expirationDate'])
            if 'secure' in cookie:
                cookie_dict['secure'] = cookie['secure']
            if 'httpOnly' in cookie:
                cookie_dict['httpOnly'] = cookie['httpOnly']
            
            driver.add_cookie(cookie_dict)
        except Exception as e:
            logger.warning(f"Failed to add cookie {cookie.get('name')}: {e}")
    
    logger.info(f"✓ Cookies loaded")


def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(TYPING_DELAY_MIN, TYPING_DELAY_MAX))


# ============================================================================
# CAPTCHA HANDLING
# ============================================================================

def check_and_close_captcha(driver: webdriver.Chrome) -> bool:
    captcha_indicators = ["Drag the slider", "Verify you are human", "puzzle", "verification"]
    
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        captcha_found = any(indicator.lower() in page_text for indicator in captcha_indicators)
        
        if captcha_found:
            logger.warning("⚠️ CAPTCHA detected! Attempting to close...")
            
            close_selectors = [
                "//button[contains(@aria-label, 'Close')]",
                "//button[contains(@class, 'close')]",
                "//*[name()='svg' and contains(@class, 'close')]/parent::button",
                "//button[text()='×']",
            ]
            
            for selector in close_selectors:
                try:
                    close_btn = driver.find_element(By.XPATH, selector)
                    if close_btn.is_displayed():
                        close_btn.click()
                        logger.info("✓ Closed captcha popup")
                        time.sleep(2)
                        return True
                except:
                    continue
            
            try:
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                logger.info("✓ Pressed ESC to close captcha")
                time.sleep(2)
                return True
            except:
                pass
        
        return False
    except:
        return False


# ============================================================================
# MESSAGE BUTTON DETECTION (From Inspect Element)
# ============================================================================

def find_message_button(driver: webdriver.Chrome, wait: WebDriverWait) -> object:
    logger.info("🔍 Searching for Message button...")
    
    # Priority selectors from inspect element
    xpath_selectors = [
        # EXACT from inspect element
        "//button[@data-e2e='message-button']",
        "//button[contains(@class, 'TUXButton') and @data-e2e='message-button']",
        "//button[contains(@class, 'TUXButton--secondary') and @data-e2e='message-button']",
        "//div[@class='TUXButton-label' and text()='Message']/ancestor::button",
        
        # Alternatives
        "//button[@data-e2e='user-page-message-button']",
        "//button[.//div[text()='Message']]",
        "//button[contains(text(), 'Message')]",
    ]
    
    for i, selector in enumerate(xpath_selectors, 1):
        try:
            logger.debug(f"  Trying selector #{i}...")
            button = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
            
            if button and button.is_displayed():
                logger.info(f"✓ Found Message button (selector #{i})")
                return button
        except:
            continue
    
    # CSS selectors
    css_selectors = [
        "button[data-e2e='message-button']",
        "button.TUXButton[data-e2e='message-button']",
    ]
    
    for selector in css_selectors:
        try:
            button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            if button and button.is_displayed():
                logger.info(f"✓ Found Message button (CSS)")
                return button
        except:
            continue
    
    logger.error("❌ Message button not found")
    return None


def click_message_button(driver: webdriver.Chrome, button) -> bool:
    if not button:
        return False
    
    logger.info("Clicking Message button...")
    
    # Try multiple click methods
    methods = [
        ("Normal click", lambda: button.click()),
        ("Scroll + click", lambda: (driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button), time.sleep(0.5), button.click())),
        ("JavaScript click", lambda: driver.execute_script("arguments[0].click();", button)),
        ("ActionChains", lambda: ActionChains(driver).move_to_element(button).click().perform()),
    ]
    
    for method_name, method_func in methods:
        try:
            logger.debug(f"  Trying: {method_name}")
            method_func()
            logger.info(f"✓ Clicked via {method_name}")
            time.sleep(2)
            return True
        except Exception as e:
            logger.debug(f"  {method_name} failed: {type(e).__name__}")
            continue
    
    logger.error("❌ All click methods failed")
    return False


# ============================================================================
# SEND MESSAGE FUNCTION
# ============================================================================

def send_streak_to_user(driver: webdriver.Chrome, username: str) -> bool:
    try:
        username = username.lstrip('@')
        logger.info(f"{'='*60}")
        logger.info(f"Processing @{username}")
        logger.info(f"{'='*60}")
        
        # Navigate to profile
        profile_url = f"https://www.tiktok.com/@{username}"
        logger.info(f"Navigating to {profile_url}")
        driver.get(profile_url)
        time.sleep(5)
        
        # Check captcha
        for _ in range(CAPTCHA_CHECK_ATTEMPTS):
            if check_and_close_captcha(driver):
                time.sleep(2)
            else:
                break
        
        wait = WebDriverWait(driver, WAIT_TIMEOUT)
        
        # Find and click Message button
        message_button = find_message_button(driver, wait)
        if not message_button:
            driver.save_screenshot(f"debug_no_button_{username}.png")
            return False
        
        if not click_message_button(driver, message_button):
            driver.save_screenshot(f"debug_click_failed_{username}.png")
            return False
        
        # Check captcha after click
        check_and_close_captcha(driver)
        
        # Find message input
        logger.info("Searching for message input...")
        input_selectors = [
            "//div[@contenteditable='true']",
            "//div[@data-e2e='dm-input']",
            "//div[@role='textbox']",
        ]
        
        message_input = None
        for selector in input_selectors:
            try:
                message_input = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                if message_input and message_input.is_displayed():
                    logger.info(f"✓ Found message input")
                    break
            except:
                continue
        
        if not message_input:
            logger.error("❌ Message input not found")
            driver.save_screenshot(f"debug_no_input_{username}.png")
            return False
        
        # Type and send
        message_input.click()
        time.sleep(0.5)
        
        streak_message = random.choice(STREAK_MESSAGES)
        logger.info(f"Typing: '{streak_message}'")
        human_type(message_input, streak_message)
        time.sleep(1)
        
        message_input.send_keys(Keys.RETURN)
        logger.info("✓ Message sent")
        time.sleep(2)
        
        logger.info(f"✅ Success @{username}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error @{username}: {e}")
        try:
            driver.save_screenshot(f"debug_error_{username}.png")
        except:
            pass
        return False


# ============================================================================
# MAIN BOT FUNCTION
# ============================================================================

def run_streak_bot():
    """Main bot execution function"""
    log_activity("="*70)
    log_activity(f"DAILY RUN STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_activity("="*70)
    
    driver = None
    
    try:
        # Load config
        cookies = load_cookies()
        users = load_users()
        
        if not users:
            log_activity("No users in list.txt", "ERROR")
            return
        
        # Setup browser
        driver = setup_driver()
        load_cookies_to_driver(driver, cookies)
        
        driver.get("https://www.tiktok.com")
        time.sleep(3)
        
        log_activity(f"✓ Bot ready. Processing {len(users)} users...")
        
        # Process each user
        success_count = 0
        fail_count = 0
        
        for username in users:
            for attempt in range(MAX_RETRIES):
                if send_streak_to_user(driver, username):
                    success_count += 1
                    log_activity(f"✓ @{username} - SUCCESS")
                    break
                else:
                    if attempt < MAX_RETRIES - 1:
                        log_activity(f"⚠️ @{username} - Retry {attempt+1}/{MAX_RETRIES}", "WARNING")
                        time.sleep(5)
                    else:
                        fail_count += 1
                        log_activity(f"✗ @{username} - FAILED", "ERROR")
            
            # Delay between users
            if username != users[-1]:
                delay = random.uniform(8, 15)
                logger.info(f"Waiting {delay:.1f}s before next user...")
                time.sleep(delay)
        
        # Summary
        log_activity("="*70)
        log_activity(f"DAILY RUN COMPLETED")
        log_activity(f"Results: {success_count}/{len(users)} successful")
        log_activity(f"Success: {success_count}, Failed: {fail_count}")
        log_activity("="*70)
        
    except Exception as e:
        log_activity(f"Critical error: {e}", "ERROR")
        import traceback
        log_activity(traceback.format_exc(), "ERROR")
        
    finally:
        if driver:
            try:
                driver.quit()
                log_activity("Browser closed")
            except:
                pass


# ============================================================================
# DAILY SCHEDULER
# ============================================================================

def start_daily_scheduler():
    """Start the daily scheduler loop"""
    
    # Parse send time
    try:
        hour, minute = map(int, SEND_TIME.split(':'))
        target_time = dt_time(hour, minute)
    except:
        logger.error(f"Invalid SEND_TIME format: {SEND_TIME}. Use HH:MM (24-hour)")
        return
    
    # Schedule the job
    schedule.every().day.at(SEND_TIME).do(run_streak_bot)
    
    print()
    print("="*70)
    print("🤖 TikTok Streak Bot - Daily Scheduler Active")
    print("="*70)
    print()
    print(f"📅 Daily execution time: {SEND_TIME} (24-hour format)")
    print(f"📁 Cookies: {COOKIES_FILE}")
    print(f"👥 Users: {USERS_FILE}")
    print(f"📝 Logs: {LOG_FILE}")
    print()
    print("="*70)
    
    # Calculate next run
    now = datetime.now()
    today_run = datetime.combine(now.date(), target_time)
    
    if now.time() < target_time:
        next_run = today_run
    else:
        from datetime import timedelta
        next_run = today_run + timedelta(days=1)
    
    time_until = next_run - now
    hours_until = int(time_until.total_seconds() / 3600)
    minutes_until = int((time_until.total_seconds() % 3600) / 60)
    
    print(f"⏰ Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏰ Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏳ Time until next run: {hours_until}h {minutes_until}m")
    print()
    print("="*70)
    print()
    print("✅ Scheduler is running... Bot will execute automatically daily.")
    print("💡 Keep this window open. Press Ctrl+C to stop.")
    print()
    print("📊 Status updates:")
    print("-" * 70)
    
    log_activity(f"Scheduler started. Next run at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Main loop
    last_check = datetime.now()
    
    while True:
        try:
            # Run pending jobs
            schedule.run_pending()
            
            # Status update every 15 minutes
            now = datetime.now()
            if (now - last_check).total_seconds() >= 900:  # 15 minutes
                # Recalculate next run
                if now.time() < target_time:
                    next_run = datetime.combine(now.date(), target_time)
                else:
                    from datetime import timedelta
                    next_run = datetime.combine(now.date(), target_time) + timedelta(days=1)
                
                time_until = next_run - now
                hours = int(time_until.total_seconds() / 3600)
                minutes = int((time_until.total_seconds() % 3600) / 60)
                
                status = f"[{now.strftime('%H:%M:%S')}] ✓ Scheduler active. Next run in {hours}h {minutes}m ({next_run.strftime('%Y-%m-%d %H:%M')})"
                print(status)
                log_activity(f"Scheduler heartbeat. Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
                last_check = now
            
            # Sleep for 1 minute
            time.sleep(60)
            
        except KeyboardInterrupt:
            print()
            print("="*70)
            print("⚠️  Scheduler stopped by user (Ctrl+C)")
            print("="*70)
            log_activity("Scheduler stopped by user")
            break
        except Exception as e:
            error_msg = f"Scheduler error: {e}"
            print(f"❌ {error_msg}")
            log_activity(error_msg, "ERROR")
            print("⏳ Retrying in 60 seconds...")
            time.sleep(60)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════╗
    ║   TikTok Streak Bot - Daily Loop Edition      ║
    ║   Automatic Daily Execution 🔄                 ║
    ╚════════════════════════════════════════════════╝
    """)
    
    try:
        start_daily_scheduler()
    except KeyboardInterrupt:
        print("\n✓ Bot stopped gracefully")
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        log_activity(f"Fatal error: {e}", "ERROR")