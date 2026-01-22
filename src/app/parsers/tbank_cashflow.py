from __future__ import annotations

from datetime import datetime, date
import re
from typing import Any

from app.parsers.base import BaseParser
from app.utils.money import decimal_to_str, parse_money_to_decimal
from app.utils.pdf import PdfMeta


_DOC_MARKERS = (
    "справка о движении средств",
    "ао «тбанк»",
)

_PERIOD_RE = re.compile(r"за период с\s+(\d{2}\.\d{2}\.\d{4})\s+по\s+(\d{2}\.\d{2}\.\d{4})", re.I)
_BAL_RE = re.compile(r"Сумма доступного остатка на\s+(\d{2}\.\d{2}\.\d{4}):\s*([\d\s]+[\.,]\d{2}\s*₽)", re.I)
_OWNER_RE = re.compile(r"\n([А-ЯЁ][^\n]+)\nАдрес места жительства:", re.M)
_ADDRESS_RE = re.compile(r"Адрес места жительства:\s*([^\n]+)", re.I)
_CONTRACT_DATE_RE = re.compile(r"Дата заключения договора:\s*(\d{2}\.\d{2}\.\d{4})", re.I)
_CONTRACT_NO_RE = re.compile(r"Номер договора:\s*(\d+)", re.I)
_ACCOUNT_NO_RE = re.compile(r"Номер лицевого счета:\s*(\d+)", re.I)
_DOC_DATE_RE = re.compile(r"\n(\d{2}\.\d{2}\.\d{4})\n", re.M)
_TOTALS_IN_RE = re.compile(r"Пополнения:\s*([\d\s]+,\d{2}\s*₽)", re.I)
_TOTALS_OUT_RE = re.compile(r"Расходы:\s*([\d\s]+,\d{2}\s*₽)", re.I)

# Typical embedded-text layout for this TBank PDF:
# Line A: "<op_date> <writeoff_date> <amount1> <amount2> <desc_part> <card_last4>"
# Line B: "<op_time> <writeoff_time> <desc_cont...>"
_LINE_A_RE = re.compile(
    r"""(?x)
    ^(?P<op_date>\d{2}\.\d{2}\.\d{4})\s+
    (?P<wo_date>\d{2}\.\d{2}\.\d{4})\s+
    (?P<amount1>[+-]?\s*[\d\s]+[\.,]\d{2}\s*₽)\s+
    (?P<amount2>[+-]?\s*[\d\s]+[\.,]\d{2}\s*₽)\s+
    (?P<desc>.+?)\s+
    (?P<card>\d{4}|—)\s*$
    """
)
_LINE_B_RE = re.compile(
    r"""(?x)
    ^(?P<op_time>\d{2}:\d{2})\s+
    (?P<wo_time>\d{2}:\d{2})
    (?:\s+(?P<desc2>.*))?$
    """
)
_DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")
_AMOUNT_PAIR_RE = re.compile(
    r"""(?x)
    ^(?P<amount1>[+-]?\s*[\d\s]+[\.,]\d{2}\s*₽)\s+
    (?P<amount2>[+-]?\s*[\d\s]+[\.,]\d{2}\s*₽)\s+
    (?P<desc>.+)$
    """
)
_CARD_RE = re.compile(r"^(?P<card>\d{4}|—)$")

# Header line sometimes merges column names into one line.
_TABLE_HEADER_HINT = "Дата и время"


def _ddmmyyyy_to_date(s: str) -> date:
    return datetime.strptime(s, "%d.%m.%Y").date()


def _ddmmyyyy_hhmm_to_dt(d: str, t: str) -> datetime:
    return datetime.strptime(f"{d} {t}", "%d.%m.%Y %H:%M")


def _clean_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("￾", " ")).strip()


def _extract_transactions(text_pages: list[str]) -> list[dict[str, Any]]:
    # In the sample, pages 1..7 are the transaction table; page 8 is totals/signature.
    lines: list[str] = []
    for p in text_pages[:7]:
        # splitlines keeps order produced by extractor
        lines.extend([ln.strip() for ln in p.splitlines() if ln.strip()])

    # Skip everything before the table header (if present).
    start_idx = 0
    for i, ln in enumerate(lines):
        if _TABLE_HEADER_HINT in ln:
            start_idx = i + 1
            break
    lines = lines[start_idx:]

    out: list[dict[str, Any]] = []
    i = 0
    while i < len(lines):
        m_a = _LINE_A_RE.match(lines[i])
        if not m_a:
            if i + 4 < len(lines):
                op_date = lines[i]
                op_time = lines[i + 1]
                wo_date = lines[i + 2]
                wo_time = lines[i + 3]
                if (
                    _DATE_RE.match(op_date)
                    and _TIME_RE.match(op_time)
                    and _DATE_RE.match(wo_date)
                    and _TIME_RE.match(wo_time)
                ):
                    m_amounts = _AMOUNT_PAIR_RE.match(lines[i + 4])
                    if m_amounts:
                        amount = parse_money_to_decimal(m_amounts.group("amount1"))
                        desc_parts = [m_amounts.group("desc")]
                        card: str | None = None
                        j = i + 5
                        while j < len(lines):
                            if _LINE_A_RE.match(lines[j]):
                                break
                            if (
                                j + 4 < len(lines)
                                and _DATE_RE.match(lines[j])
                                and _TIME_RE.match(lines[j + 1])
                                and _DATE_RE.match(lines[j + 2])
                                and _TIME_RE.match(lines[j + 3])
                                and _AMOUNT_PAIR_RE.match(lines[j + 4])
                            ):
                                break
                            if _TABLE_HEADER_HINT in lines[j]:
                                j += 1
                                continue
                            if lines[j].startswith("АО «ТБанк»") or lines[j].startswith("БИК "):
                                break
                            card_match = _CARD_RE.match(lines[j])
                            if card_match:
                                card_value = card_match.group("card")
                                card = None if card_value == "—" else card_value
                                j += 1
                                break
                            desc_parts.append(lines[j])
                            j += 1

                        desc = _clean_ws(" ".join(desc_parts))
                        out.append(
                            {
                                "op_datetime": _ddmmyyyy_hhmm_to_dt(op_date, op_time).isoformat(
                                    timespec="minutes"
                                ),
                                "writeoff_datetime": _ddmmyyyy_hhmm_to_dt(wo_date, wo_time).isoformat(
                                    timespec="minutes"
                                ),
                                "amount_rub": decimal_to_str(amount),
                                "description": desc,
                                "card_last4": card,
                            }
                        )
                        i = j
                        continue

            i += 1
            continue

        if i + 1 >= len(lines):
            break
        m_b = _LINE_B_RE.match(lines[i + 1])
        if not m_b:
            # Sometimes extractor inserts wrapped description without the expected time-line;
            # fall back to treating current line as non-transaction.
            i += 1
            continue

        op_date = m_a.group("op_date")
        wo_date = m_a.group("wo_date")
        op_time = m_b.group("op_time")
        wo_time = m_b.group("wo_time")

        amount = parse_money_to_decimal(m_a.group("amount1"))

        desc_parts = [m_a.group("desc")]
        if m_b.group("desc2"):
            desc_parts.append(m_b.group("desc2"))

        card = m_a.group("card")

        # Consume any following lines that belong to description until next Line-A or obvious footer.
        j = i + 2
        while j < len(lines):
            if _LINE_A_RE.match(lines[j]):
                break
            if lines[j].startswith("АО «ТБанк»") or lines[j].startswith("БИК "):
                break
            # Column header can reappear on next pages
            if _TABLE_HEADER_HINT in lines[j]:
                j += 1
                continue
            desc_parts.append(lines[j])
            j += 1

        desc = _clean_ws(" ".join(desc_parts))
        out.append(
            {
                "op_datetime": _ddmmyyyy_hhmm_to_dt(op_date, op_time).isoformat(timespec="minutes"),
                "writeoff_datetime": _ddmmyyyy_hhmm_to_dt(wo_date, wo_time).isoformat(timespec="minutes"),
                "amount_rub": decimal_to_str(amount),
                "description": desc,
                "card_last4": None if card == "—" else card,
            }
        )
        i = j

    return out


class TBankCashflowParser(BaseParser):
    doc_type = "tbank_cashflow_v1"

    def can_parse(self, text_pages: list[str], meta: PdfMeta) -> bool:
        if not text_pages:
            return False
        p0 = text_pages[0].lower()
        return all(m in p0 for m in _DOC_MARKERS)

    def parse(self, text_pages: list[str], meta: PdfMeta) -> dict[str, Any]:
        all_text = "\n".join(text_pages)

        owner = _OWNER_RE.search(all_text)
        address = _ADDRESS_RE.search(all_text)
        contract_date = _CONTRACT_DATE_RE.search(all_text)
        contract_no = _CONTRACT_NO_RE.search(all_text)
        account_no = _ACCOUNT_NO_RE.search(all_text)
        doc_date = _DOC_DATE_RE.search(all_text)
        period = _PERIOD_RE.search(all_text)
        balance = _BAL_RE.search(all_text)

        totals_in = _TOTALS_IN_RE.search(all_text)
        totals_out = _TOTALS_OUT_RE.search(all_text)

        transactions = _extract_transactions(text_pages)

        data: dict[str, Any] = {
            "owner_name": _clean_ws(owner.group(1)) if owner else None,
            "owner_address": _clean_ws(address.group(1)) if address else None,
            "document_date": _ddmmyyyy_to_date(doc_date.group(1)).isoformat() if doc_date else None,
            "contract_date": _ddmmyyyy_to_date(contract_date.group(1)).isoformat() if contract_date else None,
            "contract_number": contract_no.group(1) if contract_no else None,
            "account_number": account_no.group(1) if account_no else None,
            "available_balance_rub": decimal_to_str(parse_money_to_decimal(balance.group(2))) if balance else None,
            "period": {
                "start": _ddmmyyyy_to_date(period.group(1)).isoformat(),
                "end": _ddmmyyyy_to_date(period.group(2)).isoformat(),
            } if period else None,
            "transactions": transactions,
            "totals": {
                "income_rub": decimal_to_str(parse_money_to_decimal(totals_in.group(1))) if totals_in else None,
                "expense_rub": decimal_to_str(parse_money_to_decimal(totals_out.group(1))) if totals_out else None,
            },
        }

        return {
            "meta": {
                "pages": meta.pages,
                "title": meta.title,
                "author": meta.author,
                "producer": meta.producer,
                "creator": meta.creator,
                "subject": meta.subject,
            },
            "data": data,
        }
