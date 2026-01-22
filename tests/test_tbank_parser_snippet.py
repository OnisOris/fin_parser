from app.parsers.tbank_cashflow import TBankCashflowParser
from app.utils.pdf import PdfMeta


def test_tbank_can_parse() -> None:
    parser = TBankCashflowParser()
    meta = PdfMeta(pages=1, title=None, author=None, producer=None, creator=None, subject=None)
    assert parser.can_parse(["АО «ТБАНК»\nСправка о движении средств"], meta)


def test_tbank_parse_one_tx() -> None:
    parser = TBankCashflowParser()
    meta = PdfMeta(pages=8, title=None, author=None, producer=None, creator=None, subject=None)

    page1 = """АО «ТБАНК»
Справка о движении средств
22.01.2026
Иванов Иван Иванович
Адрес места жительства: Москва
Сумма доступного остатка на 22.01.2026: 48 388.72 ₽
Движение средств за период с 01.01.2026 по 22.01.2026
22.01.2026
11:08
22.01.2026
11:09
-400.00 ₽ -400.00 ₽ Внешний перевод по
номеру телефона
+79522362282
9824
"""
    page8 = """Пополнения: 126 191,00 ₽
Расходы: 86 342,67 ₽
"""

    out = parser.parse([page1, "", "", "", "", "", "", page8], meta)
    data = out["data"]
    assert data["owner_name"] == "Иванов Иван Иванович"
    assert data["available_balance_rub"] == "48388.72"
    assert data["period"]["start"] == "2026-01-01"
    assert data["period"]["end"] == "2026-01-22"
    assert data["totals"]["income_rub"] == "126191.00"
    assert data["totals"]["expense_rub"] == "86342.67"
    assert len(data["transactions"]) == 1
    tx = data["transactions"][0]
    assert tx["amount_rub"] == "-400.00"
    assert tx["card_last4"] == "9824"
    assert "Внешний перевод" in tx["description"]
