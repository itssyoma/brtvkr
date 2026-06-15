const { test, expect } = require("@playwright/test");

async function loginAsTeacher(page) {
  await page.goto("/accounts/login/");
  await page.getByLabel("Имя пользователя").fill("teacher");
  await page.getByLabel("Пароль").fill("teacher12345");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).toHaveURL(/\/dashboard\/$/);
}

test("главная страница и форма входа открываются", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Электронный журнал" })
  ).toBeVisible();
  await page.getByRole("link", { name: "Войти в систему" }).click();
  await expect(
    page.getByRole("heading", { name: "Вход в систему" })
  ).toBeVisible();
});

test("ошибочный пароль показывает понятное сообщение", async ({ page }) => {
  await page.goto("/accounts/login/");
  await page.getByLabel("Имя пользователя").fill("teacher");
  await page.getByLabel("Пароль").fill("wrong-password");
  await page.getByRole("button", { name: "Войти" }).click();

  await expect(
    page.getByText("Неверное имя пользователя или пароль.")
  ).toBeVisible();
});

test("преподаватель открывает журнал и режим редактирования", async ({
  page,
}) => {
  await loginAsTeacher(page);

  await expect(
    page.getByRole("heading", { name: "Мои дисциплины" })
  ).toBeVisible();
  const demoAssignment = page
    .locator('.data-list a[href^="/assignments/"]')
    .filter({
      hasText: "Основы программирования",
    })
    .filter({
      hasText: "Группа ИСП-21 ·",
    });
  await expect(demoAssignment).toHaveCount(1);
  await demoAssignment.click();

  await expect(
    page.getByRole("heading", { name: "Сводный журнал" })
  ).toBeVisible();
  await expect(page.locator(".summary-table")).toBeVisible();
  await expect(page.locator(".lesson-sidebar")).toBeVisible();

  await page.getByRole("link", { name: "Изменить" }).click();
  const gradeEditors = page.locator(".grade-editor");
  const attendanceEditors = page.locator(".attendance-editor");
  expect(await gradeEditors.count()).toBeGreaterThan(0);
  expect(await attendanceEditors.count()).toBeGreaterThan(0);

  const gradeBox = await gradeEditors.first().boundingBox();
  const attendanceBox = await attendanceEditors.first().boundingBox();

  expect(gradeBox).not.toBeNull();
  expect(attendanceBox).not.toBeNull();
  expect(attendanceBox.x).toBeGreaterThan(gradeBox.x);
  expect(Math.abs(attendanceBox.y - gradeBox.y)).toBeLessThan(4);
});
