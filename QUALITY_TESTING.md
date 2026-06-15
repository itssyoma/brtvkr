# Тестирование качества

Документ описывает воспроизводимые проверки электронного журнала. Перед
локальными испытаниями приложение должно быть запущено:

```bash
docker compose up -d
docker compose exec web python manage.py seed_demo
```

Команда `seed_demo` создаёт безопасные демонстрационные учётные записи и
данные. Не запускайте нагрузочный тест на рабочей базе колледжа.

## Функциональные и security-тесты Django

```bash
docker compose exec web python manage.py test --settings=config.settings_test
```

Набор проверяет права ролей, запрет изменения архивных лет, аудит изменений,
CSRF-защиту, защитные HTTP-заголовки и основные операции журнала.

Проверка производственных настроек:

```bash
docker compose exec web python manage.py check --deploy
```

Для реального сервера в `.env` должны быть включены:

```dotenv
DEBUG=0
SECURE_SSL_REDIRECT=1
SESSION_COOKIE_SECURE=1
CSRF_COOKIE_SECURE=1
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=1
SECURE_HSTS_PRELOAD=1
```

Включать эти параметры следует только после настройки HTTPS.

## UI и кросс-браузерное тестирование

Playwright проверяет Chromium, Firefox и WebKit. WebKit используется как
приближение к Safari.

Первый запуск:

```bash
npm install
npx playwright install
```

Запуск:

```bash
npm run test:e2e
```

Проверяются главная страница, форма входа, обработка неверного пароля,
кабинет преподавателя, таблица журнала и расположение полей оценки и
посещаемости. HTML-отчёт сохраняется в `playwright-report`.

## Нагрузочное тестирование

Базовый профиль для локального испытания:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.quality.yml \
  run --rm locust \
  -f /mnt/locust/locustfile.py \
  --host http://web:8000 \
  --headless \
  --users 20 \
  --spawn-rate 2 \
  --run-time 2m \
  --csv /results/load \
  --html /results/load.html
```

Сценарий имитирует чтение преподавателем главной страницы, личного кабинета
и журнала дисциплины. Результаты сохраняются в `quality/results`.

Для ВКР рекомендуется последовательно выполнить профили на 10, 25 и 50
одновременных пользователей. В таблицу результатов следует перенести:

- количество запросов;
- среднее и 95-й перцентиль времени ответа;
- число и процент ошибок;
- количество запросов в секунду.

## Анализ безопасности

Локальная установка инструментов:

```bash
python3 -m pip install -r requirements-quality.txt
```

Проверки:

```bash
bandit -r journal config \
  -x journal/tests.py,journal/migrations,journal/management/commands/seed_demo.py \
  -ll

pip-audit -r requirements.txt
```

Bandit анализирует исходный код, а `pip-audit` проверяет опубликованные
уязвимости библиотек. Все четыре группы тестов также запускаются workflow
`Quality checks` в GitHub Actions.
