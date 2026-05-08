"""
Калькулятор налогов с зарплаты в Казахстане (2026)
Kazakhstan Salary Tax Calculator (2026)
Stape — Global Contractor Payroll
"""

import streamlit as st
import requests

st.set_page_config(
    page_title="Kazakhstan Salary Taxes 2026 | Stape",
    page_icon="🇰🇿",
    layout="centered",
)

# ── Константы 2026 года / 2026 constants ─────────────────────────────────────
MRP = 4_325
MZP = 85_000
TAX_DEDUCTION = 30 * MRP

OPV_BASE_CAP = 50 * MZP
VOSMS_BASE_CAP = 20 * MZP
OOSMS_BASE_CAP = 40 * MZP
SO_BASE_MIN = 1 * MZP
SO_BASE_MAX = 7 * MZP
SN_BASE_MIN = 14 * MRP
IPN_PROGRESSIVE_THRESHOLD_MONTH = (8_500 * MRP) / 12

# ── Курс валют / FX rate ─────────────────────────────────────────────────────
# API key must be set in Streamlit secrets:
#   .streamlit/secrets.toml
#       EXCHANGERATES_API_KEY = "your_key_here"
# Get a key at https://exchangeratesapi.io
# If the secret is missing, the calculator still works — USD reference is just hidden.
EXCHANGERATES_URL = "https://api.exchangeratesapi.io/v1/latest"

# ─────────────────────────────────────────────────────────────────────────────
# Translations / Переводы
# ─────────────────────────────────────────────────────────────────────────────
TRANSLATIONS = {
    "ru": {
        "title": "Налоги с зарплаты в Казахстане",
        "subtitle": (
            "Введите оклад, чтобы рассчитать удержания работника, "
            "платежи работодателя и сумму на руки. "
            "Расчёт по законодательству РК на 2026 год."
        ),
        "rates_label": "Ставки 2026",
        "deduction_pill": "Вычет 30 МРП",
        "input_card_title": "Параметры расчёта",
        "salary_label": "Оклад (гросс), ₸",
        "salary_help": "Используйте пробел как разделитель тысяч, например: 500 000",
        "salary_negative": "Оклад должен быть 0 или больше.",
        "salary_invalid": "«{raw}» — не число для поля «Оклад».",
        "fx_unavailable": "⚠ Курс USD недоступен ({err})",
        "fx_rate_at": "курс на",
        "is_resident": "Резидент РК (или ЕАЭС с ВНЖ)",
        "is_resident_help": (
            "Иностранцы не из ЕАЭС без ВНЖ не платят ОПВ, ВОСМС, ООСМС "
            "и не имеют права на вычет ИПН."
        ),
        "deduction_label": "Вычет 30 МРП (129 750 ₸)",
        "deduction_help": (
            "Применяется только для резидентов по основному месту работы "
            "(по заявлению сотрудника)."
        ),
        "is_pensioner": "Пенсионер",
        "is_pensioner_help": "За пенсионеров не уплачиваются ОПВ, СО, ООСМС, ВОСМС.",
        "pay_opvr": "Уплачивать ОПВР",
        "pay_opvr_help": (
            "ОПВР не уплачивается за сотрудников до 1975 г.р., пенсионеров "
            "и инвалидов I-II групп."
        ),
        "net_label": "💰 На руки сотруднику",
        "net_sub": "Это {pct}% от оклада · удержания {amt}",
        "gross_label": "📋 Оклад (гросс)",
        "cost_label": "🏢 Стоимость для работодателя",
        "section_employee": "Удержания с работника",
        "section_employer": "Платежи работодателя сверху",
        "expander_title": "🔍 Как это рассчитано (пошагово)",
        "table_item": "Платёж",
        "table_formula": "Формула",
        "table_base": "База",
        "table_result": "Результат",
        "table_take_home": "На руки",
        "table_employer_total": "Итого сверху",
        "table_total_cost_line": "**Стоимость для работодателя:** {gross} + {emp_total} = **{total}**",
        "deduction_applied": "вычет",
        "deduction_not_applied": "не применяется",
        "progressive_note": (
            "⚠ **Прогрессивная ставка 15%** на сумму превышения {threshold}/мес "
            "(годовой порог 8 500 МРП)."
        ),
        "expander_caption": (
            "МРП 2026 = 4 325 ₸ · МЗП 2026 = 85 000 ₸ · Вычет 30 МРП = 129 750 ₸ · "
            "Лимиты: ОПВ — 50 МЗП, ВОСМС — 20 МЗП, ООСМС — 40 МЗП, "
            "СО — 1–7 МЗП, СН — мин. 14 МРП."
        ),
        "footer": (
            "Налоговый кодекс РК (ст. 401–437, гл. 56) · Социальный кодекс РК · "
            "Закон РК «О республиканском бюджете на 2026–2028 годы»<br>"
            "Stape — Global Contractor Payroll · 242 локации, фиксированная плата за выплату"
        ),
        "pill_tt": {
            "opv": "Обязательные пенсионные взносы. Удерживаются из зарплаты работника и перечисляются в ЕНПФ на его индивидуальный пенсионный счёт. База ограничена 50 МЗП в месяц.",
            "vosms": "Взносы на обязательное социальное медицинское страхование. Удерживаются из зарплаты работника, перечисляются в ФСМС. Дают право на бесплатную медпомощь по ОСМС. База ограничена 20 МЗП.",
            "ipn": "Индивидуальный подоходный налог. Удерживается с дохода работника после ОПВ, ВОСМС и налогового вычета 30 МРП. На годовой доход свыше 8 500 МРП применяется ставка 15%.",
            "opvr": "Обязательные пенсионные взносы работодателя. Уплачиваются работодателем сверх оклада в ЕНПФ на условно-накопительный счёт работника. С 2026 года ставка повышена с 2,5% до 3,5%.",
            "so": "Социальные отчисления. Уплачиваются работодателем в Госфонд социального страхования. Дают работнику право на пособия по безработице, потере кормильца, инвалидности. База — в коридоре 1–7 МЗП.",
            "oosms": "Отчисления на обязательное социальное медицинское страхование. Уплачиваются работодателем в ФСМС сверх оклада. Финансируют систему ОСМС. База ограничена 40 МЗП.",
            "sn": "Социальный налог. Уплачивается работодателем в бюджет. С 2026 года взаимозачёт с СО упразднён — 6% уплачиваются полностью. Минимальная база — 14 МРП.",
            "deduction": "Стандартный налоговый вычет 30 МРП = 129 750 ₸ в 2026 году. Уменьшает базу для ИПН. Применяется только для резидентов по основному месту работы (по заявлению сотрудника).",
        },
        "help": {
            "opv": (
                "**Обязательные пенсионные взносы.**\n\n"
                "Удерживаются из зарплаты работника и перечисляются работодателем "
                "в Единый накопительный пенсионный фонд (ЕНПФ) на индивидуальный "
                "пенсионный счёт сотрудника.\n\n"
                "**База:** оклад, ограничение 50 МЗП в месяц (4 250 000 ₸ в 2026).\n\n"
                "Не уплачиваются за пенсионеров и за иностранцев не из ЕАЭС без ВНЖ."
            ),
            "vosms": (
                "**Взносы на обязательное социальное медицинское страхование.**\n\n"
                "Удерживаются из зарплаты работника, перечисляются в Фонд социального "
                "медицинского страхования (ФСМС). Дают право на бесплатную медпомощь "
                "по системе ОСМС.\n\n"
                "**База:** оклад, ограничение 20 МЗП в месяц (1 700 000 ₸). "
                "Максимальный взнос — 34 000 ₸/мес.\n\n"
                "Не уплачиваются за пенсионеров и за иностранцев не из ЕАЭС без ВНЖ."
            ),
            "ipn": (
                "**Индивидуальный подоходный налог.**\n\n"
                "Удерживается с дохода работника после уменьшения на ОПВ, ВОСМС "
                "и налоговый вычет 30 МРП (если применяется).\n\n"
                "**Формула:** (оклад − ОПВ − ВОСМС − вычет) × 10%\n\n"
                "**Прогрессия:** на годовой доход свыше 8 500 МРП "
                "(~3 063 542 ₸/мес) применяется ставка 15%.\n\n"
                "Уплачивается в бюджет."
            ),
            "opvr": (
                "**Обязательные пенсионные взносы работодателя.**\n\n"
                "Уплачиваются работодателем сверх оклада в ЕНПФ на условно-"
                "накопительный счёт работника.\n\n"
                "**С 2026 года** ставка повышена с 2,5% до 3,5%.\n\n"
                "**Не уплачиваются за:**\n"
                "- сотрудников, родившихся до 01.01.1975\n"
                "- пенсионеров\n"
                "- инвалидов I и II групп (бессрочно)\n"
                "- иностранцев не из ЕАЭС без ВНЖ"
            ),
            "oosms": (
                "**Отчисления на обязательное социальное медицинское страхование.**\n\n"
                "Уплачиваются работодателем сверх оклада в ФСМС. "
                "Финансируют систему ОСМС.\n\n"
                "**База:** оклад, ограничение 40 МЗП в месяц (3 400 000 ₸).\n\n"
                "Не уплачиваются за пенсионеров и за иностранцев не из ЕАЭС без ВНЖ."
            ),
            "so": (
                "**Социальные отчисления.**\n\n"
                "Уплачиваются работодателем в Государственный фонд социального "
                "страхования (ГФСС). Дают работнику право на пособия:\n"
                "- по временной нетрудоспособности\n"
                "- по беременности и родам\n"
                "- по уходу за ребёнком\n"
                "- по потере кормильца\n"
                "- по безработице\n\n"
                "**Формула:** (оклад − ОПВ) × 5%\n\n"
                "**Коридор базы:** 1–7 МЗП (85 000 – 595 000 ₸/мес)."
            ),
            "sn": (
                "**Социальный налог.**\n\n"
                "Уплачивается работодателем в бюджет.\n\n"
                "**С 2026 года** взаимозачёт с СО упразднён — 6% уплачиваются "
                "полностью без вычета социальных отчислений.\n\n"
                "**Формула:** (оклад − ОПВ − ВОСМС) × 6%\n\n"
                "**Минимальная база:** 14 МРП (60 550 ₸/мес).\n\n"
                "ИП и ТОО на упрощёнке освобождены от уплаты СН."
            ),
        },
        "row_opv": "оклад × 10%",
        "row_vosms": "оклад × 2%",
        "row_ipn": "(оклад − ОПВ − ВОСМС − вычет) × 10%",
        "row_take_home": "оклад − ОПВ − ВОСМС − ИПН",
        "row_opvr": "оклад × 3,5%",
        "row_so": "(оклад − ОПВ) × 5%",
        "row_oosms": "оклад × 3%",
        "row_sn": "(оклад − ОПВ − ВОСМС) × 6%",
        "row_employer_total": "ОПВР + СО + ООСМС + СН",
        "corridor_so": "(коридор 1–7 МЗП)",
        "min_sn": "(мин. 14 МРП)",
        "ipn_deduction_inline": "вычет: `{deduction}`",
    },
    "en": {
        "title": "Salary taxes in Kazakhstan",
        "subtitle": (
            "Enter the gross salary to calculate employee deductions, "
            "employer payments, and the take-home amount. "
            "Calculation per Republic of Kazakhstan tax law for 2026."
        ),
        "rates_label": "2026 Rates",
        "deduction_pill": "Deduction 30 MRP",
        "input_card_title": "Calculation parameters",
        "salary_label": "Gross salary, ₸",
        "salary_help": "Use space as thousands separator, e.g.: 500 000",
        "salary_negative": "Salary must be 0 or greater.",
        "salary_invalid": "'{raw}' is not a valid number for 'Salary'.",
        "fx_unavailable": "⚠ USD rate unavailable ({err})",
        "fx_rate_at": "rate on",
        "is_resident": "KZ resident (or EAEU with permit)",
        "is_resident_help": (
            "Foreigners outside EAEU and without a residence permit do not pay "
            "OPV, VOSMS, OOSMS and are not eligible for the IPN deduction."
        ),
        "deduction_label": "Deduction 30 MRP (129 750 ₸)",
        "deduction_help": (
            "Applies only to residents at their primary place of employment "
            "(requires employee application)."
        ),
        "is_pensioner": "Pensioner",
        "is_pensioner_help": "OPV, SO, OOSMS, VOSMS are not paid for pensioners.",
        "pay_opvr": "Pay OPVR (employer pension)",
        "pay_opvr_help": (
            "OPVR is not paid for employees born before 1975, pensioners, "
            "and Group I-II disability holders."
        ),
        "net_label": "💰 Employee take-home",
        "net_sub": "{pct}% of gross · deductions {amt}",
        "gross_label": "📋 Gross salary",
        "cost_label": "🏢 Total employer cost",
        "section_employee": "Employee deductions",
        "section_employer": "Employer payments on top",
        "expander_title": "🔍 How it's calculated (step by step)",
        "table_item": "Item",
        "table_formula": "Formula",
        "table_base": "Base",
        "table_result": "Result",
        "table_take_home": "Take-home",
        "table_employer_total": "Total on top",
        "table_total_cost_line": "**Total employer cost:** {gross} + {emp_total} = **{total}**",
        "deduction_applied": "deduction",
        "deduction_not_applied": "not applied",
        "progressive_note": (
            "⚠ **Progressive 15% rate** applied to amounts exceeding {threshold}/month "
            "(annual threshold 8,500 MRP)."
        ),
        "expander_caption": (
            "MRP 2026 = 4 325 ₸ · MZP 2026 = 85 000 ₸ · Deduction 30 MRP = 129 750 ₸ · "
            "Caps: OPV — 50 MZP, VOSMS — 20 MZP, OOSMS — 40 MZP, "
            "SO — 1–7 MZP, SN — min. 14 MRP."
        ),
        "footer": (
            "Tax Code of Kazakhstan (art. 401–437, ch. 56) · Social Code of Kazakhstan · "
            "Law of RK 'On the Republican Budget for 2026–2028'<br>"
            "Stape — Global Contractor Payroll · 242 locations, flat fee per payout"
        ),
        "pill_tt": {
            "opv": "Mandatory Pension Contribution. Withheld from the employee's salary and remitted to the Unified Pension Fund (UAPF) into their individual pension account. Base capped at 50 MZP per month.",
            "vosms": "Mandatory Social Health Insurance Contribution from employee. Withheld from the employee's salary, remitted to the Social Health Insurance Fund (SHIF). Grants free medical care under the OSMS system. Base capped at 20 MZP.",
            "ipn": "Individual Income Tax. Withheld from the employee's income after OPV, VOSMS and the 30 MRP standard deduction. A 15% rate applies to annual income exceeding 8,500 MRP.",
            "opvr": "Mandatory Employer Pension Contribution. Paid by the employer on top of the salary into UAPF on a notional pension account. From 2026 the rate is increased from 2.5% to 3.5%.",
            "so": "Social Contributions. Paid by the employer to the State Social Insurance Fund. Entitle the employee to unemployment, loss-of-breadwinner and disability benefits. Base in the 1–7 MZP corridor.",
            "oosms": "Mandatory Social Health Insurance Deductions from employer. Paid by the employer to SHIF on top of the salary. Finance the OSMS system. Base capped at 40 MZP.",
            "sn": "Social Tax. Paid by the employer to the budget. From 2026 the offset against SO is abolished — the full 6% is paid. Minimum base is 14 MRP.",
            "deduction": "Standard tax deduction 30 MRP = 129,750 ₸ in 2026. Reduces the base for IPN. Applies only to residents at their primary place of employment (by employee application).",
        },
        "help": {
            "opv": (
                "**Mandatory Pension Contribution.**\n\n"
                "Withheld from the employee's salary and remitted by the employer "
                "to the Unified Accumulative Pension Fund (UAPF) into the employee's "
                "individual pension account.\n\n"
                "**Base:** salary, capped at 50 MZP per month (4,250,000 ₸ in 2026).\n\n"
                "Not paid for pensioners or for non-EAEU foreigners without a residence permit."
            ),
            "vosms": (
                "**Mandatory Social Health Insurance Contribution from employee.**\n\n"
                "Withheld from the employee's salary, remitted to the Social Health "
                "Insurance Fund (SHIF). Provides access to free medical care under "
                "the OSMS system.\n\n"
                "**Base:** salary, capped at 20 MZP per month (1,700,000 ₸). "
                "Max contribution — 34,000 ₸/month.\n\n"
                "Not paid for pensioners or for non-EAEU foreigners without a residence permit."
            ),
            "ipn": (
                "**Individual Income Tax.**\n\n"
                "Withheld from the employee's income after reducing by OPV, VOSMS "
                "and the 30 MRP standard deduction (when applicable).\n\n"
                "**Formula:** (salary − OPV − VOSMS − deduction) × 10%\n\n"
                "**Progression:** a 15% rate applies to annual income exceeding 8,500 MRP "
                "(~3,063,542 ₸/month).\n\n"
                "Paid into the state budget."
            ),
            "opvr": (
                "**Mandatory Employer Pension Contribution.**\n\n"
                "Paid by the employer on top of the salary to UAPF on a notional "
                "pension account for the employee.\n\n"
                "**From 2026** the rate is increased from 2.5% to 3.5%.\n\n"
                "**Not paid for:**\n"
                "- employees born before 01.01.1975\n"
                "- pensioners\n"
                "- Group I and II disability holders (permanent)\n"
                "- non-EAEU foreigners without a residence permit"
            ),
            "oosms": (
                "**Mandatory Social Health Insurance Deductions from employer.**\n\n"
                "Paid by the employer on top of the salary to SHIF. "
                "Finances the OSMS system.\n\n"
                "**Base:** salary, capped at 40 MZP per month (3,400,000 ₸).\n\n"
                "Not paid for pensioners or for non-EAEU foreigners without a residence permit."
            ),
            "so": (
                "**Social Contributions.**\n\n"
                "Paid by the employer to the State Social Insurance Fund (GFSS). "
                "Entitle the employee to benefits for:\n"
                "- temporary disability\n"
                "- pregnancy and childbirth\n"
                "- childcare\n"
                "- loss of breadwinner\n"
                "- unemployment\n\n"
                "**Formula:** (salary − OPV) × 5%\n\n"
                "**Base corridor:** 1–7 MZP (85,000 – 595,000 ₸/month)."
            ),
            "sn": (
                "**Social Tax.**\n\n"
                "Paid by the employer to the state budget.\n\n"
                "**From 2026** the offset against SO is abolished — the full 6% is "
                "paid without deducting social contributions.\n\n"
                "**Formula:** (salary − OPV − VOSMS) × 6%\n\n"
                "**Minimum base:** 14 MRP (60,550 ₸/month).\n\n"
                "Sole proprietors and LLPs on the simplified regime are exempt from SN."
            ),
        },
        "row_opv": "salary × 10%",
        "row_vosms": "salary × 2%",
        "row_ipn": "(salary − OPV − VOSMS − deduction) × 10%",
        "row_take_home": "salary − OPV − VOSMS − IPN",
        "row_opvr": "salary × 3.5%",
        "row_so": "(salary − OPV) × 5%",
        "row_oosms": "salary × 3%",
        "row_sn": "(salary − OPV − VOSMS) × 6%",
        "row_employer_total": "OPVR + SO + OOSMS + SN",
        "corridor_so": "(1–7 MZP corridor)",
        "min_sn": "(min. 14 MRP)",
        "ipn_deduction_inline": "deduction: `{deduction}`",
    },
}

# ── Тема / Theme ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp {
    background: radial-gradient(ellipse at 75% 5%, #3b1068 0%, #160730 45%, #080810 100%);
    color: #ffffff;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 4rem;
    max-width: 720px;
}

h1, h2, h3 { color: #ffffff !important; font-weight: 800 !important; }

label,
.stNumberInput label,
.stTextInput label,
.stCheckbox label { color: #b8a8d8 !important; font-size: 0.82rem !important; font-weight: 500 !important; }
.stCheckbox label p { color: #ffffff !important; font-size: 0.9rem !important; }

.stTextInput input, .stNumberInput input {
    background-color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 8px !important;
    color: #111111 !important;
    font-size: 0.95rem !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 2px rgba(124,58,237,0.28) !important;
}

.input-card {
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px;
    padding: 1.6rem 1.8rem 1.2rem;
    margin-bottom: 1.4rem;
}
.input-card-title {
    color: #e2d4ff;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    margin-bottom: 1.1rem;
}

.stape-rates-bar {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    background: rgba(124,58,237,0.1);
    border: 1px solid rgba(124,58,237,0.22);
    border-radius: 10px;
    padding: 0.5rem 1rem;
    margin-bottom: 1.8rem;
    flex-wrap: wrap;
}
.stape-rates-bar .bar-label {
    color: #9b87c2; font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.08em; white-space: nowrap;
}
.stape-rates-bar .pill {
    background: rgba(167,139,250,0.13);
    border: 1px solid rgba(167,139,250,0.25);
    border-radius: 20px;
    color: #c4b5e8;
    font-size: 0.78rem; font-weight: 600;
    padding: 0.15rem 0.65rem; white-space: nowrap; cursor: help;
}

.usd-ref {
    color: #c4b5e8; font-size: 0.78rem;
    margin-top: -0.6rem; margin-bottom: 0.8rem; padding-left: 2px;
}
.usd-ref b { color: #e2d4ff; font-weight: 600; }
.usd-ref .rate { color: #9b87c2; font-size: 0.7rem; }

[data-testid="stMetric"] {
    background: rgba(255,255,255,0.065);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 1rem 1.1rem !important;
}
[data-testid="stMetricLabel"] { color: #b8a8d8 !important; font-size: 0.75rem !important; }
[data-testid="stMetricValue"] { color: #ffffff !important; font-size: 1.35rem !important; font-weight: 700 !important; }
[data-testid="stMetricDelta"] { font-size: 0.82rem !important; }

[data-testid="stTooltipIcon"] svg,
[data-testid="stTooltipHoverTarget"] svg,
button[data-testid="stTooltipHoverTarget"] svg {
    color: #c4b5e8 !important; fill: #c4b5e8 !important; opacity: 0.85 !important;
}
[data-testid="stTooltipIcon"]:hover svg,
[data-testid="stTooltipHoverTarget"]:hover svg,
button[data-testid="stTooltipHoverTarget"]:hover svg {
    color: #e2d4ff !important; fill: #e2d4ff !important; opacity: 1 !important;
}
[data-baseweb="tooltip"] strong,
[role="tooltip"] strong,
[data-testid="stTooltipContent"] strong,
div[class*="tooltip"] strong,
div[class*="Tooltip"] strong,
div[data-baseweb*="tooltip"] strong {
    color: #000000 !important; font-weight: 700 !important;
}
[data-baseweb="tooltip"] code,
[role="tooltip"] code,
[data-testid="stTooltipContent"] code {
    color: #1a1a1a !important;
    background: rgba(124,58,237,0.12) !important;
    padding: 1px 5px !important; border-radius: 3px !important;
}

.savings-banner-green {
    background: linear-gradient(135deg, rgba(16,185,129,0.22), rgba(5,150,105,0.14));
    border: 1.5px solid rgba(52,211,153,0.55);
    border-radius: 16px;
    padding: 1.6rem 2rem;
    text-align: center;
    margin: 1.2rem 0;
    box-shadow: 0 0 32px rgba(16,185,129,0.12);
}
.savings-banner-green .s-label { color: #6ee7b7; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 0.3rem; }
.savings-banner-green .s-value { color: #34d399; font-size: 2.6rem; font-weight: 800; line-height: 1.1; text-shadow: 0 0 24px rgba(52,211,153,0.45); }
.savings-banner-green .s-sub { color: #6ee7b7; font-size: 0.88rem; margin-top: 0.4rem; opacity: 0.9; }
.savings-banner-green .s-usd { color: #6ee7b7; font-size: 0.95rem; margin-top: 0.2rem; opacity: 0.75; font-weight: 600; }

.banner-purple {
    background: linear-gradient(135deg, rgba(124,58,237,0.32), rgba(79,36,158,0.22));
    border: 1px solid rgba(167,139,250,0.42);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.banner-purple .b-label { color: #c4b5e8; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; }
.banner-purple .b-value { color: #ffffff; font-size: 1.5rem; font-weight: 700; line-height: 1.2; margin-top: 0.2rem; }
.banner-purple .b-sub { color: #c4b5e8; font-size: 0.75rem; opacity: 0.85; margin-top: 0.15rem; }

.section-title {
    color: #b8a8d8;
    font-size: 0.78rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin: 1.5rem 0 0.6rem 0;
}

[data-testid="stButton"] button {
    padding: 4px 0 !important;
    min-height: unset !important;
    height: 36px !important;
    border-radius: 20px !important;
    font-size: 1.15rem !important;
    line-height: 1 !important;
    transition: all 0.15s !important;
}
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed, #5b21b6) !important;
    border: 1px solid rgba(167,139,250,0.6) !important;
    color: #ffffff !important;
    box-shadow: 0 2px 10px rgba(124,58,237,0.45) !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background: linear-gradient(135deg, #8b4dee, #6d28d9) !important;
    transform: translateY(-1px);
}
[data-testid="stButton"] button[kind="secondary"] {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(167,139,250,0.28) !important;
    color: #c4b5e8 !important;
    box-shadow: none !important;
}
[data-testid="stButton"] button[kind="secondary"]:hover {
    background: rgba(167,139,250,0.16) !important;
    border-color: rgba(167,139,250,0.55) !important;
    color: #ffffff !important;
}
[data-testid="stButton"] button p {
    color: inherit !important; font-size: inherit !important; margin: 0 !important;
}

hr { border-color: rgba(255,255,255,0.08) !important; }

.streamlit-expanderHeader,
[data-testid="stExpander"] summary {
    color: #b8a8d8 !important;
    background: rgba(255,255,255,0.03) !important;
    border-radius: 8px !important;
}
.streamlit-expanderContent,
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    background: rgba(255,255,255,0.02) !important;
    color: #d4c8f0 !important;
    border-radius: 0 0 8px 8px !important;
}
[data-testid="stExpander"] p,
[data-testid="stExpander"] li,
[data-testid="stExpander"] td,
[data-testid="stExpander"] th { color: #d4c8f0 !important; }
[data-testid="stExpander"] code { color: #e2d4ff !important; background: rgba(124,58,237,0.18) !important; }

.stCaption { color: rgba(255,255,255,0.4) !important; }
.stAlert { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Language switcher (top-right) — RU is default · флаги
# ─────────────────────────────────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "ru"


def _set_lang_ru():
    st.session_state.lang = "ru"


def _set_lang_en():
    st.session_state.lang = "en"


_, sw_col = st.columns([5, 1])
with sw_col:
    btn_ru, btn_en = st.columns(2, gap="small")
    with btn_ru:
        st.button(
            "🇷🇺",
            key="lang_ru_btn",
            type="primary" if st.session_state.lang == "ru" else "secondary",
            on_click=_set_lang_ru,
            use_container_width=True,
            help="Русский",
        )
    with btn_en:
        st.button(
            "🇬🇧",
            key="lang_en_btn",
            type="primary" if st.session_state.lang == "en" else "secondary",
            on_click=_set_lang_en,
            use_container_width=True,
            help="English",
        )

LANG = st.session_state.lang
T = TRANSLATIONS[LANG]

# ── Логотип Stape ────────────────────────────────────────────────────────────
_LOGO_B64 = "PHN2ZyB3aWR0aD0iNTg0IiBoZWlnaHQ9IjI5MiIgdmlld0JveD0iMCAwIDU4NCAyOTIiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxnIGNsaXAtcGF0aD0idXJsKCNjbGlwMF8zNjcxXzQwNzQpIj4KPHBhdGggZD0iTTE4My4xNTEgMTcwLjI3NkMxOTAuNDQ2IDE3OC40OTIgMTk5LjQ3NyAxODIuNjAxIDIxMC4yNDMgMTgyLjYwMUMyMTUuMTMxIDE4Mi42MDEgMjE5LjA0NCAxODEuNjI3IDIyMS45ODQgMTc5LjY3OUMyMjUuNDU0IDE3Ny4zMDYgMjI3LjE5IDE3NC4wMTIgMjI3LjE5IDE2OS43OThDMjI3LjE5IDE2NS45NzMgMjI1LjY4NCAxNjIuODU3IDIyMi42NzQgMTYwLjQ0OEMyMjAuNjkxIDE1OC44NTUgMjE1LjkxIDE1Ni41NzEgMjA4LjMzMSAxNTMuNTk2TDIwNi4zMTIgMTUyLjc5OUwyMDIuNyAxNTEuMzY1QzIwMi40NTIgMTUxLjI1OCAyMDIuMDA5IDE1MS4wODEgMjAxLjM3MiAxNTAuODMzQzE5My41ODEgMTQ3Ljg5NCAxODguNTM0IDE0NS40NjggMTg2LjIzMiAxNDMuNTU1QzE4NS44NzggMTQzLjIzNyAxODUuNDM1IDE0Mi43OTQgMTg0LjkwNCAxNDIuMjI3QzE4MS4xMTQgMTM4LjE1NSAxNzkuMjIgMTMzLjI1IDE3OS4yMiAxMjcuNTEyQzE3OS4yMiAxMjAuMTExIDE4MS44NzYgMTE0LjE0MyAxODcuMTg4IDEwOS42MUMxOTIuNzQ4IDEwNC44NjQgMjAwLjI1NiAxMDIuNDkyIDIwOS43MTIgMTAyLjQ5MkMyMTYuMjk5IDEwMi40OTIgMjIyLjE3OCAxMDMuNDY2IDIyNy4zNDkgMTA1LjQxM0MyMzEuNDU3IDEwNy4wMDcgMjM1LjU0OCAxMDkuNDUxIDIzOS42MiAxMTIuNzQ0TDIzMi4yODkgMTIyLjk0NEMyMjYuMDIxIDExNi45OTQgMjE4LjUzMSAxMTQuMDE5IDIwOS44MTggMTE0LjAxOUMyMDQuMTE3IDExNC4wMTkgMTk5Ljk3MyAxMTUuMzQ3IDE5Ny4zODggMTE4LjAwM0MxOTUuMTkyIDEyMC4yNyAxOTQuMDk0IDEyMy4wMTUgMTk0LjA5NCAxMjYuMjM3QzE5NC4wOTQgMTI5LjkyMSAxOTUuNjg4IDEzMi44NiAxOTguODc1IDEzNS4wNTZDMjAwLjg5NCAxMzYuNDcyIDIwNS4xNzkgMTM4LjM0OSAyMTEuNzMxIDE0MC42ODdMMjE1Ljk4MSAxNDIuMjI3QzIyNS4zMyAxNDUuNTkyIDIzMS43NCAxNDguODg1IDIzNS4yMTEgMTUyLjEwOEMyNDAuMDI4IDE1Ni42MDYgMjQyLjQzNiAxNjIuMjU1IDI0Mi40MzYgMTY5LjA1NEMyNDIuNDM2IDE3Ny40ODMgMjM5LjEyNCAxODQuMDUzIDIzMi41MDIgMTg4Ljc2M0MyMjcuMDQ4IDE5Mi42MjMgMjE5LjYxMSAxOTQuNTUzIDIxMC4xOSAxOTQuNTUzQzE5NS41MjggMTk0LjU1MyAxODMuNzg4IDE4OS41NzcgMTc0Ljk3IDE3OS42MjZMMTgzLjE1MSAxNzAuMjc2Wk0yNzguMzIxIDEwOC4zODhWMTI4LjQxNkgyOTguMzQ4VjEzOC41MDlIMjc4LjMyMVYxNzMuNDFDMjc4LjMyMSAxNzYuODQ2IDI3OC43MjggMTc5LjIxOSAyNzkuNTQzIDE4MC41MjlDMjgwLjY0MSAxODIuMzM1IDI4Mi40NjUgMTgzLjIzOCAyODUuMDE1IDE4My4yMzhDMjg4LjE2NyAxODMuMjM4IDI5MS40MDcgMTgxLjk5OSAyOTQuNzM2IDE3OS41MkwyOTguMTM2IDE4OS40QzI5Mi45NjUgMTkyLjY5NCAyODcuNTExIDE5NC4zNDEgMjgxLjc3NCAxOTQuMzQxQzI3NS44MjQgMTk0LjM0MSAyNzEuMzI3IDE5Mi41NyAyNjguMjgxIDE4OS4wMjhDMjY1Ljc2NyAxODYuMDg5IDI2NC41MDkgMTgxLjgzOSAyNjQuNTA5IDE3Ni4yNzlWMTM4LjUwOUgyNTAuMTY2VjEyOC40MTZIMjY0LjUwOVYxMTQuNzFMMjc4LjMyMSAxMDguMzg4Wk0zNDkuMTA4IDE1MS4yNThWMTUwLjI0OUMzNDkuMTA4IDE0MS41MDEgMzQ0Ljk0NyAxMzcuMTI4IDMzNi42MjQgMTM3LjEyOEMzMjguODMzIDEzNy4xMjggMzIxLjgyMSAxMzkuNDgzIDMxNS41ODggMTQ0LjE5M0wzMTAuMTY5IDEzNC4zNjVDMzE4LjM1IDEyOS4wMTggMzI3LjMyOCAxMjYuMzQ0IDMzNy4xMDIgMTI2LjM0NEMzNDYuNTIzIDEyNi4zNDQgMzUzLjU1MyAxMjkuMDUzIDM1OC4xOTIgMTM0LjQ3MkMzNjEuNDE1IDEzOC4xOSAzNjMuMDI2IDE0My42NzkgMzYzLjAyNiAxNTAuOTRWMTczLjM1N0MzNjMuMDI2IDE4MS42NDQgMzY0LjMwMSAxODguMDU1IDM2Ni44NTEgMTkyLjU4OEgzNTMuODg5QzM1Mi4zNjYgMTg5LjY0OCAzNTEuMzU3IDE4Ni4yODQgMzUwLjg2MSAxODIuNDk0SDM1MC40ODlDMzQ4LjY4MyAxODYuMDM2IDM0NS43NzkgMTg5LjAyOCAzNDEuNzc3IDE5MS40NzJDMzM4LjUxOSAxOTMuNDU1IDMzNC4yMTYgMTk0LjQ0NyAzMjguODY4IDE5NC40NDdDMzIyLjUyOSAxOTQuNDQ3IDMxNy4yODggMTkyLjU4OCAzMTMuMTQ0IDE4OC44NjlDMzA4LjgyMyAxODQuOTczIDMwNi42NjMgMTgwLjAxNSAzMDYuNjYzIDE3My45OTVDMzA2LjY2MyAxNTguODM3IDMxOC45MTcgMTUxLjI1OCAzNDMuNDI0IDE1MS4yNThIMzQ5LjEwOFpNMzQ5LjEwOCAxNjEuMjQ1SDM0NC44NThDMzM2LjU3MSAxNjEuMjQ1IDMzMC4zNTYgMTYyLjMwOCAzMjYuMjEyIDE2NC40MzNDMzIyLjY3MSAxNjYuMjM5IDMyMC45IDE2OS4zNTUgMzIwLjkgMTczLjc4MkMzMjAuOSAxNzYuNzU3IDMyMS45NjMgMTc5LjExMiAzMjQuMDg3IDE4MC44NDhDMzI2LjEwNiAxODIuNTEyIDMyOC43MjcgMTgzLjM0NCAzMzEuOTUgMTgzLjM0NEMzMzYuMjM1IDE4My4zNDQgMzQwLjA3NyAxODEuODIyIDM0My40NzcgMTc4Ljc3NkMzNDcuMjMxIDE3NS40NDcgMzQ5LjEwOCAxNzEuMTYyIDM0OS4xMDggMTY1LjkyVjE2MS4yNDVaTTM5NC45MjggMTI4LjQxNlYxMzcuMTI4QzQwMC44MDYgMTMwLjE1MSA0MDguMTkxIDEyNi42NjIgNDE3LjA4IDEyNi42NjJDNDI2LjAwNCAxMjYuNjYyIDQzMy4xOTQgMTI5LjYzNyA0MzguNjQ4IDEzNS41ODdDNDQzLjg1NCAxNDEuMjE4IDQ0Ni40NTcgMTQ4Ljc5NyA0NDYuNDU3IDE1OC4zMjRDNDQ2LjQ1NyAxNjYuMzYzIDQ0NC41OTcgMTczLjA5MiA0NDAuODc5IDE3OC41MUM0MzUuNTMxIDE4Ni4zMDIgNDI3LjY2OSAxOTAuMTk3IDQxNy4yOTIgMTkwLjE5N0M0MDcuODcyIDE5MC4xOTcgNDAwLjc3MSAxODYuOTc0IDM5NS45OSAxODAuNTI5VjIwMi44NEgzODEuNzUzVjEyOC40MTZIMzk0LjkyOFpNMzk1Ljk5IDE2OC4yMDRDNDAxLjA5IDE3NS41MzUgNDA3LjA0IDE3OS4yMDEgNDEzLjgzOSAxNzkuMjAxQzQxOS4yNTggMTc5LjIwMSA0MjMuNTQzIDE3Ny40MTIgNDI2LjY5NSAxNzMuODM1QzQyOS45NTMgMTcwLjE1MiA0MzEuNTgyIDE2NC45MjkgNDMxLjU4MiAxNTguMTY0QzQzMS41ODIgMTUyLjAzNyA0MzAuMjE5IDE0Ny4yMjEgNDI3LjQ5MiAxNDMuNzE1QzQyNC4zNzUgMTM5Ljc0OCA0MTkuODI0IDEzNy43NjUgNDEzLjgzOSAxMzcuNzY1QzQwOS41NTQgMTM3Ljc2NSA0MDUuNzExIDEzOS4xMTEgNDAyLjMxMiAxNDEuODAyQzM5OS42NTUgMTQzLjg5MiAzOTcuNTQ4IDE0Ni43NjEgMzk1Ljk5IDE1MC40MDhWMTY4LjIwNFpNNTE4LjM1OSAxNjMuMjY0SDQ3MC40OTZDNDcwLjc0NCAxNjguODk1IDQ3Mi41MTQgMTczLjQ2NCA0NzUuODA4IDE3Ni45N0M0NzkuNzc0IDE4MS4xMTMgNDg0LjgyMSAxODMuMTg1IDQ5MC45NDggMTgzLjE4NUM0OTguMTczIDE4My4xODUgNTA0LjU2NSAxNzkuODAzIDUxMC4xMjUgMTczLjAzOUw1MTguNjI1IDE4MS42NDRDNTExLjY0OCAxOTAuNDI3IDUwMS45OCAxOTQuODE5IDQ4OS42MiAxOTQuODE5QzQ3OS40OTEgMTk0LjgxOSA0NzEuMzI4IDE5MS41NzggNDY1LjEzIDE4NS4wOTdDNDU5LjIxNiAxNzguODY0IDQ1Ni4yNTkgMTcwLjgyNSA0NTYuMjU5IDE2MC45OEM0NTYuMjU5IDE1Mi45NzYgNDU4LjE4OSAxNDYuMDE3IDQ2Mi4wNDkgMTQwLjEwM0M0NjUuNDg0IDEzNC44NjEgNDcwLjA3MSAxMzEuMDU0IDQ3NS44MDggMTI4LjY4MUM0NzkuNzM5IDEyNy4wNTIgNDgzLjkzNiAxMjYuMjM3IDQ4OC4zOTggMTI2LjIzN0M0OTUuNTE2IDEyNi4yMzcgNTAxLjU5IDEyOC4yMjEgNTA2LjYxOSAxMzIuMTg3QzUxMS44MjUgMTM2LjIyNSA1MTUuMzMxIDE0MS44NzMgNTE3LjEzNyAxNDkuMTMzQzUxNy45NTIgMTUyLjQyNyA1MTguMzU5IDE1NS44OTggNTE4LjM1OSAxNTkuNTQ1VjE2My4yNjRaTTUwNC4xMjIgMTUyLjkwNUM1MDMuODM5IDE0OS4yNTcgNTAyLjg4MyAxNDYuMjEyIDUwMS4yNTQgMTQzLjc2OEM0OTguMTczIDEzOS4yNyA0OTMuNzQ2IDEzNy4wMjEgNDg3Ljk3MyAxMzcuMDIxQzQ4Mi44MDIgMTM3LjAyMSA0NzguNTUzIDEzOS4xMTEgNDc1LjIyNCAxNDMuMjlDNDczLjE2OSAxNDUuODc1IDQ3MS44OTQgMTQ5LjA4IDQ3MS4zOTkgMTUyLjkwNUg1MDQuMTIyWiIgZmlsbD0id2hpdGUiLz4KPHBhdGggZD0iTTEyNi45MzQgNzYuODcyQzEyNy4yMTUgODcuMDU0OSAxMjIuOTU0IDkzLjYzOTMgMTE0LjI4NCA5OC43MjMzQzEwMy42NjcgMTA0Ljk0OSA5Mi42OTY1IDExMS4zNTQgODIuMDA3NiAxMTcuNTA1QzcwLjE2MzMgMTI0LjMyMSA2Ny4yMTQgMTMyLjY1NCA3NS43MTk2IDE0My42NDFDNzIuOTUzOSAxNDkuNzA0IDYzLjMxNTcgMTQ4LjU5IDU3Ljk5NzMgMTQ3LjcxMUM1Mi4wMzg5IDE0NC4wODggNTAuMzA0MSAxMzYuMTcgNTAuNjQyNSAxMjkuNjlDNTEuMTIzNyAxMjAuNDc5IDU2LjAwNTggMTExLjcxNCA2Mi42OTQ3IDEwNS40ODVDODQuMDYwNCA4OS4zNzc2IDEwNS40NTMgNzMuMzA0NCAxMjYuODc4IDU3LjI3NjVDMTI2Ljg3NyA2My44MDgzIDEyNi44OTggNzAuMzQwNyAxMjYuOTM0IDc2Ljg3MloiIGZpbGw9IiM3OTY1RTYiLz4KPHBhdGggZD0iTTc1LjcxODcgMTQzLjY0MkM3NS43MTg3IDE0My42NDIgNzQuNDI1OCAxNDIuNTk0IDcyLjI5NTUgMTQwLjY5NUM2Mi4xOTU1IDEzMS42OSA0OS4wMTA4IDExNy43NjggNjIuNjkzOCAxMDUuNDg1QzU4LjE4NjEgMTA4LjkwMSA1NC40MTY2IDExMy4wMjggNTEuMTY1NCAxMTcuMzhDNDEuNDg1MiAxMzAuMzQxIDQzLjM2OTkgMTUxLjE5MyA0My44MzU1IDE2Ni43NDlDNDQuMDU5NSAxNzQuMjI3IDUyLjg5MzYgMTc1Ljg4NiA1OC41MTE4IDE3Mi44OTZDNjQuNjk5MSAxNjkuNjA1IDcxLjMgMTY1LjkxMSA3Ny4yODcxIDE2Mi42ODhDODYuNDcxOCAxNTcuNzQyIDgxLjk1MyAxNDguNjU4IDc1LjcxODcgMTQzLjY0MloiIGZpbGw9IiM3OTY1RTYiLz4KPHBhdGggZD0iTTQ0LjE0OTkgMjExLjc1MkM0My44Njk1IDIwMS41NjkgNDguMTI4NCAxOTQuOTg1IDU2LjgwMTUgMTg5LjkwMUM2Ny40MjAyIDE4My42NzcgNzguMzg5NiAxNzcuMjY3IDg5LjA3NTcgMTcxLjExOEMxMDAuOTE4IDE2NC4zMDUgMTAzLjg3IDE1NS45NjggOTUuMzY0OCAxNDQuOTgzQzk4LjEzMjEgMTM4LjkxOSAxMDcuNzY5IDE0MC4wMzUgMTEzLjA4OCAxNDAuOTEzQzExOS4wNDQgMTQ0LjUzOCAxMjAuNzc4IDE1Mi40NTcgMTIwLjQ0MSAxNTguOTM0QzExOS45NjIgMTY4LjEzOSAxMTUuMDc2IDE3Ni45MDkgMTA4LjM5IDE4My4xNEM4Ny4wMjI5IDE5OS4yNDYgNjUuNjMxMiAyMTUuMzE5IDQ0LjIwNTIgMjMxLjM0OEM0NC4yMDYzIDIyNC44MTYgNDQuMTg2OSAyMTguMjg0IDQ0LjE0OTkgMjExLjc1MloiIGZpbGw9IiM3OTY1RTYiLz4KPHBhdGggZD0iTTk1LjM2ODkgMTQ0Ljk4NEM5NS4zNjg5IDE0NC45ODQgOTYuNjYxMyAxNDYuMDMyIDk4Ljc5MTYgMTQ3LjkzMUMxMDguODk1IDE1Ni45MzggMTIyLjA3MyAxNzAuODUzIDEwOC4zOTUgMTgzLjE0MUMxMTIuOTAzIDE3OS43MjYgMTE2LjY2OSAxNzUuNTk5IDExOS45MjEgMTcxLjI0NkMxMjkuNjA0IDE1OC4yODQgMTI3LjcyMSAxMzcuNDMgMTI3LjI1MiAxMjEuODc3QzEyNy4wMjYgMTE0LjM5OCAxMTguMTk2IDExMi43NCAxMTIuNTc2IDExNS43MjlDMTA2LjM4NyAxMTkuMDIxIDk5Ljc4NyAxMjIuNzE0IDkzLjgwMDUgMTI1LjkzOUM4NC42MTYzIDEzMC44ODYgODkuMTM0NiAxMzkuOTY2IDk1LjM2ODkgMTQ0Ljk4NFoiIGZpbGw9IiM3OTY1RTYiLz4KPC9nPgo8ZGVmcz4KPGNsaXBQYXRoIGlkPSJjbGlwMF8zNjcxXzQwNzQiPgo8cmVjdCB3aWR0aD0iNTg0IiBoZWlnaHQ9IjI5MiIgZmlsbD0id2hpdGUiLz4KPC9jbGlwUGF0aD4KPC9kZWZzPgo8L3N2Zz4K"

st.markdown(
    f'<img src="data:image/svg+xml;base64,{_LOGO_B64}" height="48" '
    f'style="display:block; margin-bottom:1rem;" />',
    unsafe_allow_html=True,
)
st.markdown(
    f"<h1 style='color:white;font-size:1.9rem;font-weight:800;margin-bottom:0.25rem;'>"
    f"{T['title']}</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<p style='color:#b8a8d8;margin-bottom:1.4rem;font-size:0.95rem;'>{T['subtitle']}</p>",
    unsafe_allow_html=True,
)


# ── Хелперы / Helpers ────────────────────────────────────────────────────────
def fmt_kzt(n: float) -> str:
    return f"{n:,.0f}".replace(",", " ") + " ₸"


def fmt_usd(n: float) -> str:
    return f"${n:,.2f}".replace(",", " ")


def parse_int_input(raw: str):
    cleaned = raw.replace(" ", "").replace(",", "").strip()
    if not cleaned:
        return 0, None
    try:
        val = int(cleaned)
        if val < 0:
            return None, T["salary_negative"]
        return val, None
    except ValueError:
        return None, T["salary_invalid"].format(raw=raw)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_kzt_to_usd_rate() -> dict:
    # Read API key from Streamlit secrets only.
    try:
        api_key = st.secrets["EXCHANGERATES_API_KEY"]
    except (KeyError, FileNotFoundError, AttributeError):
        return {"rate": None, "date": "", "error": "API key not configured"}

    if not api_key:
        return {"rate": None, "date": "", "error": "API key not configured"}

    try:
        resp = requests.get(
            EXCHANGERATES_URL,
            params={"access_key": api_key, "base": "KZT", "symbols": "USD"},
            timeout=5,
        )
        data = resp.json()
        if data.get("success") and "rates" in data and "USD" in data["rates"]:
            return {"rate": data["rates"]["USD"], "date": data.get("date", ""), "error": None}
        err = data.get("error", {})
        return {"rate": None, "date": "", "error": err.get("info") or err.get("type") or "API error"}
    except Exception as e:
        return {"rate": None, "date": "", "error": str(e)}


def calculate_taxes(salary, apply_deduction, is_resident, is_pensioner, pay_opvr):
    # ОПВ / OPV (10%)
    if is_pensioner or not is_resident:
        opv = 0
    else:
        opv = round(min(salary, OPV_BASE_CAP) * 0.10)
    # ВОСМС / VOSMS (2%)
    if is_pensioner or not is_resident:
        vosms = 0
    else:
        vosms = round(min(salary, VOSMS_BASE_CAP) * 0.02)
    # ИПН / IPN (10% with deduction)
    deduction = TAX_DEDUCTION if (apply_deduction and is_resident) else 0
    ipn_base = max(0, salary - opv - vosms - deduction)
    if ipn_base > IPN_PROGRESSIVE_THRESHOLD_MONTH:
        ipn = round(IPN_PROGRESSIVE_THRESHOLD_MONTH * 0.10) + \
              round((ipn_base - IPN_PROGRESSIVE_THRESHOLD_MONTH) * 0.15)
        progressive = True
    else:
        ipn = round(ipn_base * 0.10)
        progressive = False
    net = salary - opv - vosms - ipn

    # ОПВР / OPVR (3.5%)
    if pay_opvr and not is_pensioner and is_resident:
        opvr = round(min(salary, OPV_BASE_CAP) * 0.035)
    else:
        opvr = 0
    # СО / SO (5% with corridor)
    if is_pensioner:
        so = 0
    else:
        so_base = max(SO_BASE_MIN, min(salary - opv, SO_BASE_MAX))
        so = round(so_base * 0.05)
    # ООСМС / OOSMS (3%)
    if is_pensioner or not is_resident:
        oosms = 0
    else:
        oosms = round(min(salary, OOSMS_BASE_CAP) * 0.03)
    # СН / SN (6% with min base)
    sn = round(max(salary - opv - vosms, SN_BASE_MIN) * 0.06)

    employer_total = opvr + so + oosms + sn
    total_cost = salary + employer_total
    return {
        "opv": opv, "vosms": vosms, "ipn": ipn, "net": net, "deduction": deduction,
        "opvr": opvr, "so": so, "oosms": oosms, "sn": sn,
        "employer_total": employer_total, "total_cost": total_cost,
        "ipn_progressive": progressive,
    }


# ── FX rate ──────────────────────────────────────────────────────────────────
fx = fetch_kzt_to_usd_rate()


def usd(amount_kzt):
    if fx["rate"] is None or fx["rate"] <= 0:
        return None
    return amount_kzt * fx["rate"]


# ── Pill bar with 2026 rates ─────────────────────────────────────────────────
pill_tt = T["pill_tt"]
st.markdown(f"""
<div class="stape-rates-bar">
    <span class="bar-label">{T['rates_label']}</span>
    <span class="pill" title="{pill_tt['opv']}">ОПВ 10%</span>
    <span class="pill" title="{pill_tt['vosms']}">ВОСМС 2%</span>
    <span class="pill" title="{pill_tt['ipn']}">ИПН 10%</span>
    <span class="pill" title="{pill_tt['opvr']}">ОПВР 3,5%</span>
    <span class="pill" title="{pill_tt['so']}">СО 5%</span>
    <span class="pill" title="{pill_tt['oosms']}">ООСМС 3%</span>
    <span class="pill" title="{pill_tt['sn']}">СН 6%</span>
    <span class="pill" title="{pill_tt['deduction']}">{T['deduction_pill']}</span>
</div>
""", unsafe_allow_html=True)

# ── Input card ───────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="input-card"><div class="input-card-title">{T["input_card_title"]}</div>',
    unsafe_allow_html=True,
)

raw_salary = st.text_input(T["salary_label"], value="500 000", help=T["salary_help"])
salary_val, salary_err = parse_int_input(raw_salary)
if salary_err:
    st.error(salary_err)
salary = salary_val if salary_val is not None else 0

# USD reference under salary
if fx["rate"] is not None and salary > 0:
    salary_usd = salary * fx["rate"]
    rate_per_usd = 1 / fx["rate"]
    usd_str = f"{salary_usd:,.2f}".replace(",", " ")
    rate_str = f"{rate_per_usd:,.2f}".replace(",", " ")
    st.markdown(
        f"""<div class="usd-ref">
        <b>≈ ${usd_str}</b> USD <span class="rate">·
        {T["fx_rate_at"]} {fx["date"]}: $1 = {rate_str} ₸</span>
        </div>""",
        unsafe_allow_html=True,
    )
elif fx["rate"] is None:
    st.markdown(
        f'<div class="usd-ref"><span class="rate">{T["fx_unavailable"].format(err=fx["error"])}</span></div>',
        unsafe_allow_html=True,
    )

# Status checkboxes
col_a, col_b = st.columns(2)
with col_a:
    is_resident = st.checkbox(T["is_resident"], value=True, help=T["is_resident_help"])
    apply_deduction = st.checkbox(
        T["deduction_label"], value=True, disabled=not is_resident, help=T["deduction_help"],
    )
with col_b:
    is_pensioner = st.checkbox(T["is_pensioner"], value=False, help=T["is_pensioner_help"])
    pay_opvr = st.checkbox(
        T["pay_opvr"], value=True, disabled=is_pensioner, help=T["pay_opvr_help"],
    )

st.markdown('</div>', unsafe_allow_html=True)

# ── Compute and render ───────────────────────────────────────────────────────
if not salary_err and salary > 0:
    r = calculate_taxes(
        salary=salary,
        apply_deduction=apply_deduction,
        is_resident=is_resident,
        is_pensioner=is_pensioner,
        pay_opvr=pay_opvr,
    )
    employee_total = r["opv"] + r["vosms"] + r["ipn"]

    # Hero green banner — net pay
    net_pct = (r["net"] / salary * 100) if salary else 0
    usd_net = usd(r["net"])
    usd_line = f'<div class="s-usd">≈ {fmt_usd(usd_net)} USD</div>' if usd_net else ""
    pct_str = f"{net_pct:.1f}".replace(".", ",") if LANG == "ru" else f"{net_pct:.1f}"
    st.markdown(f"""
    <div class="savings-banner-green">
        <div class="s-label">{T["net_label"]}</div>
        <div class="s-value">{fmt_kzt(r["net"])}</div>
        {usd_line}
        <div class="s-sub">{T["net_sub"].format(pct=pct_str, amt=fmt_kzt(employee_total))}</div>
    </div>
    """, unsafe_allow_html=True)

    # Two purple banners — gross and total cost
    col_g, col_t = st.columns(2)
    usd_gross = usd(salary)
    usd_total = usd(r["total_cost"])
    with col_g:
        st.markdown(f"""
        <div class="banner-purple">
            <div class="b-label">{T["gross_label"]}</div>
            <div class="b-value">{fmt_kzt(salary)}</div>
            <div class="b-sub">{fmt_usd(usd_gross) if usd_gross else "—"}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_t:
        st.markdown(f"""
        <div class="banner-purple">
            <div class="b-label">{T["cost_label"]}</div>
            <div class="b-value">{fmt_kzt(r["total_cost"])}</div>
            <div class="b-sub">{fmt_usd(usd_total) if usd_total else "—"}</div>
        </div>
        """, unsafe_allow_html=True)

    # Employee deductions
    H = T["help"]
    st.markdown(f'<div class="section-title">{T["section_employee"]}</div>', unsafe_allow_html=True)
    e1, e2, e3 = st.columns(3)
    with e1:
        st.metric("ОПВ · 10%", fmt_kzt(r["opv"]), help=H["opv"])
    with e2:
        st.metric("ВОСМС · 2%", fmt_kzt(r["vosms"]), help=H["vosms"])
    with e3:
        st.metric("ИПН · 10%", fmt_kzt(r["ipn"]), help=H["ipn"])

    # Employer payments
    st.markdown(f'<div class="section-title">{T["section_employer"]}</div>', unsafe_allow_html=True)
    p1, p2 = st.columns(2)
    with p1:
        st.metric("ОПВР · 3,5%", fmt_kzt(r["opvr"]), help=H["opvr"])
        st.metric("ООСМС · 3%", fmt_kzt(r["oosms"]), help=H["oosms"])
    with p2:
        st.metric("СО · 5%", fmt_kzt(r["so"]), help=H["so"])
        st.metric("СН · 6%", fmt_kzt(r["sn"]), help=H["sn"])

    # Detailed step-by-step
    with st.expander(T["expander_title"]):
        deduction_str = (
            fmt_kzt(r['deduction']) if r["deduction"] > 0
            else T["deduction_not_applied"]
        )
        prog_note = ""
        if r["ipn_progressive"]:
            prog_note = "\n\n> " + T["progressive_note"].format(
                threshold=fmt_kzt(IPN_PROGRESSIVE_THRESHOLD_MONTH)
            )

        opv_base_str = fmt_kzt(min(salary, OPV_BASE_CAP))
        vosms_base_str = fmt_kzt(min(salary, VOSMS_BASE_CAP))
        oosms_base_str = fmt_kzt(min(salary, OOSMS_BASE_CAP))
        opvr_base_str = fmt_kzt(min(salary, OPV_BASE_CAP)) if r["opvr"] > 0 else "—"
        so_base_str = (
            fmt_kzt(max(SO_BASE_MIN, min(salary - r["opv"], SO_BASE_MAX)))
            if r["so"] > 0 else "—"
        )
        sn_base_str = fmt_kzt(max(salary - r["opv"] - r["vosms"], SN_BASE_MIN))

        ipn_base_inline = T["ipn_deduction_inline"].format(deduction=deduction_str)

        st.markdown(f"""
**{T["section_employee"]}**

| {T["table_item"]} | {T["table_formula"]} | {T["table_base"]} | {T["table_result"]} |
|---|---|---|---|
| **ОПВ** | {T["row_opv"]} | `{opv_base_str}` | **{fmt_kzt(r["opv"])}** |
| **ВОСМС** | {T["row_vosms"]} | `{vosms_base_str}` | **{fmt_kzt(r["vosms"])}** |
| **ИПН** | {T["row_ipn"]} | {ipn_base_inline} | **{fmt_kzt(r["ipn"])}** |
| **{T["table_take_home"]}** | {T["row_take_home"]} | — | **{fmt_kzt(r["net"])}** |
{prog_note}

**{T["section_employer"]}**

| {T["table_item"]} | {T["table_formula"]} | {T["table_base"]} | {T["table_result"]} |
|---|---|---|---|
| **ОПВР** | {T["row_opvr"]} | `{opvr_base_str}` | **{fmt_kzt(r["opvr"])}** |
| **СО** | {T["row_so"]} | `{so_base_str}` {T["corridor_so"]} | **{fmt_kzt(r["so"])}** |
| **ООСМС** | {T["row_oosms"]} | `{oosms_base_str}` | **{fmt_kzt(r["oosms"])}** |
| **СН** | {T["row_sn"]} | `{sn_base_str}` {T["min_sn"]} | **{fmt_kzt(r["sn"])}** |
| **{T["table_employer_total"]}** | {T["row_employer_total"]} | — | **{fmt_kzt(r["employer_total"])}** |

{T["table_total_cost_line"].format(
    gross=fmt_kzt(salary),
    emp_total=fmt_kzt(r["employer_total"]),
    total=fmt_kzt(r["total_cost"]),
)}
        """)

        st.caption(T["expander_caption"])

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='margin-top:2rem; color:rgba(255,255,255,0.3); "
    f"font-size:0.75rem; text-align:center;'>{T['footer']}</div>",
    unsafe_allow_html=True,
)
