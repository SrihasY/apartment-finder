from __future__ import print_function

import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import base64
from email.mime.text import MIMEText

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

SECRETS_FILE = "cool_secretive_filename.json"
NOTIFY_EMAIL = "my_email@gmail.com"
SITE_URL = "coolapartmentwebsite.com"
BUDGET = 2000

def send_email(bodytext, subjecttext):
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        message = MIMEText(bodytext)
        message['To'] = NOTIFY_EMAIL
        message['From'] = NOTIFY_EMAIL
        message['Subject'] = subjecttext

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        send_message = (service.users().messages().send(userId="me", body=create_message).execute())
        return send_message
    except HttpError as error:
        print(F'An error occurred: {error}')
        return None

# Initiate the browser
options = Options()
options.headless = True
browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

browser.get(SITE_URL)

# get and open the browser widget
try:
    element = WebDriverWait(browser, 20).until(
        EC.presence_of_element_located((By.ID, "rg-widget-feature-icons"))
    )
    panel = element.find_element(By.XPATH, '//div[1]/div[@class="zoid-outlet"]/iframe[1]')
    browser.switch_to.frame(panel)
    inpanel = WebDriverWait(browser, 20).until(
        EC.element_to_be_clickable((By.ID, "rg-widget-feature-icons"))
    )
except:
    print("Failed. Unable to open widget.")
    browser.quit()
    exit()

# open the flat prices window
try:
    button = inpanel.find_element(By.XPATH, '//div[@id="featureslayout"]/div[2]/div[1]')
    WebDriverWait(browser, 10).until(EC.element_to_be_clickable(button))
    button.click()

    browser.switch_to.default_content()
    nextframe = browser.find_element(By.CLASS_NAME, 'doorway-plugin-frame')
    browser.switch_to.frame(nextframe)
    popup = WebDriverWait(browser, 20).until(
        EC.element_to_be_clickable((By.ID, "InlineCss_PluginAvailabilities"))
    )
    popup.find_element(By.XPATH, '//div[1]/div[1]/div[1]/div[1]/button[1]').click()
    flatlist = popup.find_elements(By.XPATH, '//div[1]/div[1]/div[1]/div[1]/*[@class="doorway-availabilities-list-row"]')
except:
    print("Failed. Unable to get price list.")
    browser.quit()
    exit()

# filter prices, alert if a flat is found
with open('log.txt', 'a') as log:
    print("Prices at ", datetime.datetime.now(), ": ", file=log)
    for flat in flatlist:
        price = flat.find_element(By.CLASS_NAME, 'doorway-availabilities-list-col')
        pricestr = str(price.get_attribute("innerHTML"))
        if pricestr[0] != '$':
            # Listing without a price, indicates that a new flat was just posted
            print("Potential listing: ", datetime.datetime.now(), file=log)
            continue
        pricestr = pricestr[1:]
        pricestr = pricestr.replace(',', '')
        print(pricestr, file=log)
        # there's only so much that can be paid in a month
        if(float(pricestr) > BUDGET):
            continue
        
        bodyval = "There is a new listing in <COOL APARTMENT> at price: " + pricestr + " USD."
        send_email(bodyval, "Price Bot: New apartment listing")
        with open('new_apartments.txt', 'a') as output:
            print(datetime.datetime.now(), ": New apartment at price = ", pricestr, file=output)
            browser.quit()
            exit()

browser.quit()