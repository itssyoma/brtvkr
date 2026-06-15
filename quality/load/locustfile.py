import os
import re

from locust import HttpUser, between, task


CSRF_PATTERN = re.compile(
    r'name="csrfmiddlewaretoken" value="([^"]+)"'
)
ASSIGNMENT_PATTERN = re.compile(r'href="/assignments/(\d+)/"')


class TeacherJournalUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        login_page = self.client.get(
            "/accounts/login/",
            name="GET /accounts/login/",
        )
        token_match = CSRF_PATTERN.search(login_page.text)
        if token_match is None:
            raise RuntimeError("Не найден CSRF-токен формы входа.")

        response = self.client.post(
            "/accounts/login/",
            {
                "username": os.getenv("LOAD_USERNAME", "teacher"),
                "password": os.getenv(
                    "LOAD_PASSWORD",
                    "teacher12345",
                ),
                "csrfmiddlewaretoken": token_match.group(1),
                "next": "/dashboard/",
            },
            headers={"Referer": f"{self.host}/accounts/login/"},
            name="POST /accounts/login/",
        )
        if response.status_code != 200 or "/dashboard/" not in response.url:
            raise RuntimeError("Не удалось авторизовать нагрузочного пользователя.")

        assignment_match = ASSIGNMENT_PATTERN.search(response.text)
        self.assignment_path = (
            f"/assignments/{assignment_match.group(1)}/"
            if assignment_match
            else None
        )

    @task(3)
    def open_dashboard(self):
        self.client.get("/dashboard/", name="GET /dashboard/")

    @task(5)
    def open_journal(self):
        if self.assignment_path:
            self.client.get(
                self.assignment_path,
                name="GET /assignments/:id/",
            )

    @task(1)
    def open_home(self):
        self.client.get("/", name="GET /")
