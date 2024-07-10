import re
import time

import scrapy
from scrapy.http import Response


class PythonJobsSpider(scrapy.Spider):
    name = "python_jobs"
    allowed_domains = ["djinni.co"]
    start_urls = ["https://djinni.co/jobs/?primary_keyword=Python"]
    base_url = "https://djinni.co"

    def parse(self, response: Response, **kwargs):
        for vacancy in response.css("a.h3.job-list-item__link::attr(href)")[:5]:
            vacancy_url = self.base_url + str(vacancy.extract())
            yield response.follow(
                vacancy_url, callback=self.vacancy_detailed_page
            )

    def vacancy_detailed_page(self, response: Response, **kwargs):
        skills = response.css("div.col.pl-2::text").getall()[1]
        skills = self.clean_skills(skills)
        time.sleep(0.5)
        yield {
            "vacancy_url": response.url,
            "skills": skills,
        }

    def filter_only_skills(self, list_of_skills: list[str]) -> list[str]:
        pattern = re.compile(r"[^a-zA-Z0-9.,;:?!'\"()\[\]{}<>@#$%^&*_+=|\\/-]")
        result = []
        for skill in list_of_skills:
            if skill == pattern.sub(" ", skill):
                result.append(skill)
            else:
                return []
        return result

    def clean_skills(self, skills: str) -> list[str]:
        skills = skills.replace("\xa0", " ").replace("\n", " ").split(", ")
        skills = [skill.strip().strip("‎") for skill in skills]
        skills = self.filter_only_skills(skills)
        return skills
