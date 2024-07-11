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


class PythonJobsSpider(scrapy.Spider):
    name = "python_jobs"
    allowed_domains = ["djinni.co"]
    start_urls = ["https://djinni.co/jobs/?primary_keyword=Python"]
    base_url = "https://djinni.co"
    login_url = "https://djinni.co/login?from=frontpage_main"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        self.test_throttle = 0

    def parse(self, response: Response, **kwargs):
        self.login_to_djinni()
        self.driver.get(self.start_urls[0])
        while True:
            for vacancy in self.driver.find_elements(
                    By.CSS_SELECTOR, "a.h3.job-list-item__link"
            )[:5]:
                vacancy_url = vacancy.get_attribute("href")
                yield response.follow(
                    vacancy_url,
                    callback=self.vacancy_detailed_page,
                )

            try:
                self.test_throttle += 1
                pagination_button = self.driver.find_elements(
                    By.CSS_SELECTOR, "li.page-item a.page-link"
                )[-1]
                if pagination_button.is_displayed():
                    pagination_button.click()
                    time.sleep(1)
                else:
                    break
                if self.test_throttle == 2:
                    break
            except NoSuchElementException:
                break

    def vacancy_detailed_page(self, response: Response, **kwargs):
        time.sleep(0.5)
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

    def get_skills(self, response: Response) -> list[str]:
        skills = response.css("div.col.pl-2::text").getall()[1]
        skills = self._clean_skills(skills)
        return skills or -1

    def get_salary(self, response: Response) -> str:
        salary = response.css(
            "span.public-salary-item::text"
        ).get().strip()
        return salary or -1

    def get_english(self, response: Response) -> str:
        english_letters = string.ascii_letters
        english = response.css(
            "strong.font-weight-600.capitalize-first-letter::text"
        ).getall()[0].replace("\xa0", " ").replace("\n", " ").strip()
        """
        Check if English even required
        """
        for letter in english:
            if letter in english_letters:
                return english
        return "-1"

    def get_experience(self, response: Response) -> str:
        experience = response.css(
            "strong.font-weight-600.capitalize-first-letter::text"
        ).getall()[1].replace("\xa0", " ").replace("\n", " ").strip()
        if "досвід" in experience:
            return experience
        return "-1"

    def login_to_djinni(self) -> None:
        self.driver.get(self.login_url)
        email = self.driver.find_element(By.NAME, "email")
        email.send_keys(config("DJINNI_EMAIL"))
        password = self.driver.find_element(By.NAME, "password")
        password.send_keys(config("DJINNI_PASSWORD"))
        password.send_keys(Keys.ENTER)

    def close(self, reason):
        self.driver.quit()
