import re
import string
import time

import scrapy
from decouple import config
from scrapy.http import Response
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

EMAIL = config("DJINNI_EMAIL")
PASSWORD = config("DJINNI_PASSWORD")
MAIN_PAGE_WAIT_TIME = config("MAIN_PAGE_WAIT_TIME", cast=float, default=1)
DETAIL_PAGE_WAIT_TIME = config("DETAIL_PAGE_WAIT_TIME", cast=float, default=1)


class PythonJobsSpider(scrapy.Spider):
    name = "python_jobs"
    allowed_domains = ["djinni.co"]
    start_urls = ["https://djinni.co/jobs/?primary_keyword=Python"]
    base_url = "https://djinni.co"
    login_url = "https://djinni.co/login?from=frontpage_main"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=self.options)
        self.driver.implicitly_wait(10)

    def parse(self, response: Response, **kwargs) -> None:
        self.login_to_djinni()
        self.driver.get(self.start_urls[0])

        while True:
            for vacancy in self.driver.find_elements(
                By.CSS_SELECTOR, "a.h3.job-list-item__link"
            ):
                vacancy_url = vacancy.get_attribute("href")
                yield response.follow(
                    vacancy_url,
                    callback=self.vacancy_detailed_page,
                )

            try:
                pagination_button = self.driver.find_elements(
                    By.CSS_SELECTOR, "li.page-item a.page-link"
                )[-1]
                parent_li = pagination_button.find_element(By.XPATH, "./..")
                if "disabled" in parent_li.get_attribute("class"):
                    break

                pagination_button.click()
                time.sleep(MAIN_PAGE_WAIT_TIME)
            except NoSuchElementException:
                break

    def vacancy_detailed_page(self, response: Response, **kwargs) -> dict:
        time.sleep(DETAIL_PAGE_WAIT_TIME)
        yield {
            "skills": self.get_skills(response),
            "salary": self.get_salary(response),
            "english": self.get_english(response),
            "experience": self.get_experience(response),
            "vacancy_url": response.url,
        }

    def _filter_only_skills(self, list_of_skills: list[str]) -> list[str]:
        pattern = re.compile(r"[^a-zA-Z0-9.,;:?!'\"()\[\]{}<>@#$%^&*_+=|\\/-]")
        result = []
        for skill in list_of_skills:
            if skill == pattern.sub(" ", skill):
                result.append(skill)
            else:
                return []
        return result

    def _clean_skills(self, skills: str) -> list[str]:
        skills = skills.replace("\xa0", " ").replace("\n", " ").split(", ")
        skills = [skill.strip().strip("‎") for skill in skills]
        skills = self._filter_only_skills(skills)
        return skills

    def get_skills(self, response: Response) -> list[str] | str:
        try:
            skills = response.css("div.col.pl-2::text").getall()[1]
        except IndexError:
            return "-1"
        skills = self._clean_skills(skills)
        return skills or "-1"

    def get_salary(self, response: Response) -> str:
        try:
            salary = (
                response.css("span.public-salary-item::text").get().strip()
            )
        except IndexError:
            return "-1"
        return salary or "-1"

    def get_english(self, response: Response) -> str:
        english_letters = string.ascii_letters
        try:
            english = (
                response.css(
                    "strong.font-weight-600.capitalize-first-letter::text"
                )
                .getall()[0]
                .replace("\xa0", " ")
                .replace("\n", " ")
                .strip()
            )
        except IndexError:
            return "-1"
        """
        Check if English even required
        """
        for letter in english:
            if letter in english_letters:
                return english
        return "-1"

    def get_experience(self, response: Response) -> str:
        try:
            experience = (
                response.css(
                    "strong.font-weight-600.capitalize-first-letter::text"
                )
                .getall()[1]
                .replace("\xa0", " ")
                .replace("\n", " ")
                .strip()
            )
        except IndexError:
            return "-1"
        if "досвід" in experience or "experience" in experience:
            return experience
        return "-1"

    def login_to_djinni(self) -> None:
        self.driver.get(self.login_url)
        email = self.driver.find_element(By.NAME, "email")
        email.send_keys(EMAIL)
        password = self.driver.find_element(By.NAME, "password")
        password.send_keys(PASSWORD)
        password.send_keys(Keys.ENTER)

    def close(self, reason) -> None:
        self.driver.quit()
