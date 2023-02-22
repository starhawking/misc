import dataclasses
import getpass
import json
import random
import time
from typing import Mapping, Optional

import selenium.common.exceptions
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


WAIT_BETWEEN_PHOTOS = 2 # At least PRETEND we're maybe a human


@dataclasses.dataclass
class Photo:
    url: str
    title: str
    description: str

    raw_details: str
    details: Mapping[str,str]

    @property
    def upload_date(self):
        return self.details.get("UPLOAD DATE")

    @property
    def date_taken(self):
        return self.details.get("DATE TAKEN")

    @property
    def original_filename(self):
        return self.details.get("ORGINAL FILENAME")


def random_wait():
    time.sleep(random.random())

def load_cfg():
    try:
        with open('cfg.json') as fdesc:
            cfg = json.load(fdesc)
    except FileNotFoundError:
        cfg = {}

    if "username" not in cfg:
        cfg["username"] = input("Photobucket Username: ")
    if "password" not in cfg:
        cfg["password"] = getpass.getpass("Photobucket Password: ")

    return cfg

def load_driver(cfg):
    options=Options()
    if "profile" in cfg:
        options.set_preference('profile', cfg['profile'])
    options.set_preference("browser.download.dir", "./downloads")
    service = Service('geckodriver.exe')

    driver = Firefox(service=service, options=options)

    driver.get("https://photobucket.com/auth/login")
    return driver


def do_login(cfg, driver):
    wait = WebDriverWait(driver, 10)
    username = wait.until(EC.element_to_be_clickable((By.ID, 'username')))
    password = wait.until(EC.element_to_be_clickable((By.ID, 'password')))

    random_wait()

    username.click()
    username.send_keys(cfg['username'])

    random_wait()

    password.click()
    password.send_keys(cfg['password'])

    password.submit()

class DetailPage:
    def __init__(self, driver):
        driver.implicitly_wait(10)
        self._driver = driver

    def do_download(self):
        wait = WebDriverWait(self._driver, 10)
        download = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[id='download-button']")))

    @property
    def details(self):
        detail_section = self._driver.find_element(By.CLASS_NAME, "MuiAccordionDetails-root")
        detail_elems = detail_section.find_elements(By.CLASS_NAME, "MuiGrid-root")
        details = {}
        for detail in detail_elems:
            try:
                k, v = detail.find_elements(By.TAG_NAME, 'span')
                details[k.text.rstrip(":")] = v.text
            except ValueError:
                #print(detail)
                #print(detail.text)
                pass
        return details

    @property
    def title(self):
        return self._driver.find_element(By.CSS_SELECTOR, "input[name='title']").get_property('value')
    
    @property
    def description(self):
        return self._driver.find_element(By.CSS_SELECTOR, "textarea[name='description']").get_property('value')

    @property
    def raw_details(self):
        return self._driver.find_element(By.CLASS_NAME, "MuiAccordionDetails-root").text

    @property
    def url(self):
        return self._driver.current_url

    def as_dataclass(self):
        return Photo(
            url=self.url,
            title=self.title,
            description=self.description,
            raw_details=self.raw_details,
            details=self.details
        )


def get_image_details(driver, base_url):
    driver.get(base_url)


def handle_image(driver, image):
    detail_element_name = 'persistent-details-button'
    title_element_name = 'title'
    description_element_name = 'description'
    driver.find_element(By.CSS_SELECTOR, "button[aria-label^='next slide / item']")


def handle_gallery(driver):
    base_url = driver.current_url
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "gallery"))
    )
    current = driver.find_element(By.ID, "gallery").find_element(By.TAG_NAME, "img").click()
    driver.find_element(By.CSS_SELECTOR, "button[id='persistent-details-button']").click()
    detail_page = DetailPage(driver)
    while True:
        yield detail_page.as_dataclass()
        try:
            driver.find_element(By.CSS_SELECTOR, "button[aria-label^='next slide / item']").click()
            #driver.find_element(By.CSS_SELECTOR, "button[aria-label='previous slide / item']").click()
        except selenium.common.exceptions.NoSuchElementException:
            return
        time.sleep(WAIT_BETWEEN_PHOTOS) 

cfg = load_cfg()
driver = load_driver(cfg)
do_login(cfg, driver)


items = []
for x in handle_gallery(driver):
    print(x)
    items.append(dataclasses.asdict(x))

with open('results.json', 'w') as fdesc:
    json.dump(items, fdesc, indent=2)

