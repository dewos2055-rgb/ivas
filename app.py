#Copyright @Arslan-MD
#Updated Playwright Version

from flask import Flask, request, jsonify
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import logging
import json
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class IVASSMSClient:

    def __init__(self):

        self.base_url = "https://www.ivasms.com"

        self.logged_in = False
        self.csrf_token = None

        # PLAYWRIGHT
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        self.page = self.context.new_page()

    # =========================
    # LOAD COOKIES
    # =========================

    def load_cookies(self, file_path="cookies.json"):

        try:

            if os.getenv("COOKIES_JSON"):

                cookies_raw = json.loads(
                    os.getenv("COOKIES_JSON")
                )

                logger.debug(
                    "Loaded cookies from env"
                )

            else:

                with open(file_path, "r") as file:

                    cookies_raw = json.load(file)

                    logger.debug(
                        "Loaded cookies from file"
                    )

            if isinstance(cookies_raw, dict):

                return cookies_raw

            elif isinstance(cookies_raw, list):

                cookies = {}

                for cookie in cookies_raw:

                    if "name" in cookie and "value" in cookie:

                        cookies[cookie["name"]] = cookie["value"]

                return cookies

            return None

        except Exception as e:

            logger.error(f"Cookie load error: {e}")

            return None

    # =========================
    # LOGIN
    # =========================

    def login_with_cookies(self, cookies_file="cookies.json"):

        logger.debug(
            "Attempting login with Playwright"
        )

        cookies = self.load_cookies(cookies_file)

        if not cookies:

            logger.error("No cookies loaded")

            return False

        try:

            browser_cookies = []

            for name, value in cookies.items():

                browser_cookies.append({
                    "name": name,
                    "value": value,
                    "domain": ".ivasms.com",
                    "path": "/"
                })

            self.context.add_cookies(
                browser_cookies
            )

            self.page.goto(
                f"{self.base_url}/portal/sms/received",
                timeout=60000
            )

            self.page.wait_for_timeout(5000)

            html_content = self.page.content()

            logger.debug(
                f"Current URL: {self.page.url}"
            )

            if "login" in self.page.url.lower():

                logger.error(
                    "Redirected to login page"
                )

                return False

            soup = BeautifulSoup(
                html_content,
                "html.parser"
            )

            csrf_input = soup.find(
                "input",
                {"name": "_token"}
            )

            if csrf_input:

                self.csrf_token = csrf_input.get(
                    "value"
                )

                self.logged_in = True

                logger.debug(
                    "Login successful"
                )

                return True

            logger.error(
                "CSRF token not found"
            )

            logger.error(
                html_content[:2000]
            )

            return False

        except Exception as e:

            logger.error(f"Login error: {e}")

            return False

    # =========================
    # CHECK OTPS
    # =========================

    def check_otps(self, from_date="", to_date=""):

        if not self.logged_in:

            return None

        payload = {
            "from": from_date,
            "to": to_date,
            "_token": self.csrf_token
        }

        headers = {
            "X-Requested-With": "XMLHttpRequest"
        }

        try:

            response = self.page.request.post(
                f"{self.base_url}/portal/sms/received/getsms",
                form=payload,
                headers=headers
            )

            if response.status == 200:

                html_content = response.text()

                soup = BeautifulSoup(
                    html_content,
                    "html.parser"
                )

                sms_details = []

                items = soup.select("div.item")

                for item in items:

                    try:

                        country_number = item.select_one(
                            ".col-sm-4"
                        ).text.strip()

                        sms_details.append({
                            "country_number": country_number
                        })

                    except:
                        pass

                return {
                    "sms_details": sms_details,
                    "raw": html_content
                }

            logger.error(
                f"OTP request failed: {response.status}"
            )

            return None

        except Exception as e:

            logger.error(f"OTP error: {e}")

            return None


# =========================
# FLASK
# =========================

app = Flask(__name__)

client = IVASSMSClient()

with app.app_context():

    if not client.login_with_cookies():

        logger.error(
            "Failed initialize client"
        )


@app.route("/")
def home():

    return jsonify({
        "status": "running"
    })


@app.route("/sms")
def get_sms():

    date_str = request.args.get("date")

    if not date_str:

        return jsonify({
            "error": "date required"
        })

    try:

        datetime.strptime(
            date_str,
            "%d/%m/%Y"
        )

    except:

        return jsonify({
            "error": "invalid date"
        })

    result = client.check_otps(
        from_date=date_str
    )

    if not result:

        return jsonify({
            "error": "failed fetch"
        })

    return jsonify({
        "status": "success",
        "data": result
    })


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        debug=False
    )
