# pdf-parser-service

Небольшой **расширяемый** сервис и CLI для парсинга PDF → JSON.

- `src-layout`
- установка/запуск через **uv** (вместо pip)
- HTTP API: загрузить PDF → распарсить → вернуть JSON
- архитектура через реестр парсеров (легко добавлять новые форматы документов)

## Быстрый старт (uv)

```bash
# 1) создать окружение и поставить зависимости
uv sync

# 2) запустить HTTP сервер
uv run pdf-parser serve --host 0.0.0.0 --port 8000

# 3) или использовать CLI для локального парса
uv run pdf-parser parse --file /path/to/file.pdf
```

## HTTP API

### `POST /v1/parse`

- `multipart/form-data`
- поле: `file` (PDF)

Пример:

```bash
curl -s -X POST http://localhost:8000/v1/parse \
  -F "file=@/path/to/file.pdf" | jq
```

Ответ (примерно):

```json
{
  "doc_type": "tbank_cashflow_v1",
  "meta": { "pages": 8, "producer": "...", "title": null },
  "data": {
    "owner_name": "...",
    "available_balance_rub": "48388.72",
    "period": { "start": "2026-01-01", "end": "2026-01-22" },
    "transactions": [
      {
        "op_datetime": "2026-01-22T11:08:00",
        "writeoff_datetime": "2026-01-22T11:09:00",
        "amount_rub": "-400.00",
        "description": "Внешний перевод по номеру телефона +7952...",
        "card_last4": "9824"
      }
    ],
    "totals": { "income_rub": "126191.00", "expense_rub": "86342.67" }
  }
}
```

## Как добавлять новые парсеры

1. Создай модуль `src/app/parsers/<my_parser>.py` и класс, наследующий `BaseParser`.
2. Зарегистрируй его в `src/app/parsers/registry.py`.
3. Реализуй:
   - `can_parse(text_pages, meta) -> bool`
   - `parse(text_pages, meta) -> dict`

Сервис сам выберет подходящий парсер, либо упадёт на `GenericParser` (текст по страницам + простые метаданные).

## Структура проекта

```
pdf-parser-service/
  pyproject.toml
  README.md
  src/
    app/
      __main__.py
      api/
        server.py
      parsers/
        base.py
        registry.py
        generic.py
        tbank_cashflow.py
      utils/
        money.py
        pdf.py
  tests/
```

## Замечания по качеству парса

- Если PDF содержит **селектируемый текст**, `pdfplumber` достаёт его хорошо.
- Если PDF — **скан** (только картинки), нужен OCR. В текущей версии OCR не включён,
  но архитектура позволяет добавить `OcrTextExtractor` и переключать стратегию по необходимости.

## License

MIT
