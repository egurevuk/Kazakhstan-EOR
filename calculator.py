"""
Калькулятор налогов с зарплаты в Казахстане (2026)
Stape — Global Contractor Payroll
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ── Константы 2026 года ──────────────────────────────────────────────────────
MRP = 4_325        # Месячный расчётный показатель, тенге
MZP = 85_000       # Минимальная заработная плата, тенге
TAX_DEDUCTION_MRP = 30
TAX_DEDUCTION = TAX_DEDUCTION_MRP * MRP  # 129 750 ₸

# Лимиты баз
OPV_BASE_CAP = 50 * MZP            # 4 250 000 ₸
VOSMS_BASE_CAP = 20 * MZP          # 1 700 000 ₸ (макс. ВОСМС = 34 000)
OOSMS_BASE_CAP = 40 * MZP          # 3 400 000 ₸
SO_BASE_MIN = 1 * MZP              # 85 000 ₸
SO_BASE_MAX = 7 * MZP              # 595 000 ₸
SN_BASE_MIN = 14 * MRP             # 60 550 ₸

# ИПН прогрессия
IPN_PROGRESSIVE_THRESHOLD_MONTH = (8_500 * MRP) / 12   # ~3 063 542 ₸/мес

# ── Курс валют ───────────────────────────────────────────────────────────────
# ⚠ Для production лучше хранить ключ в st.secrets["EXCHANGERATES_API_KEY"]
EXCHANGERATES_API_KEY = "3a7e501b0c4bacf8817fa3d87fa15661"
EXCHANGERATES_URL = "https://api.exchangeratesapi.io/v1/latest"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_kzt_to_usd_rate() -> dict:
    """
    Получает актуальный курс KZT → USD от exchangeratesapi.io.
    Кэшируется на 1 час. Возвращает dict с ключами: rate, date, error.
    """
    try:
        # Пробуем взять ключ из st.secrets, иначе используем константу
        api_key = st.secrets.get("EXCHANGERATES_API_KEY", EXCHANGERATES_API_KEY) \
            if hasattr(st, "secrets") else EXCHANGERATES_API_KEY
    except Exception:
        api_key = EXCHANGERATES_API_KEY

    try:
        resp = requests.get(
            EXCHANGERATES_URL,
            params={"access_key": api_key, "base": "KZT", "symbols": "USD"},
            timeout=5,
        )
        data = resp.json()
        if data.get("success") and "rates" in data and "USD" in data["rates"]:
            return {
                "rate": data["rates"]["USD"],
                "date": data.get("date", ""),
                "error": None,
            }
        # API вернул ошибку (например, ограничение тарифа)
        err_info = data.get("error", {})
        err_msg = err_info.get("info") or err_info.get("type") or "неизвестная ошибка"
        return {"rate": None, "date": "", "error": err_msg}
    except requests.RequestException as e:
        return {"rate": None, "date": "", "error": f"сеть: {e}"}
    except Exception as e:
        return {"rate": None, "date": "", "error": str(e)}


def kzt_to_usd_str(amount_kzt: float, rate: float | None) -> str:
    """Форматирует сумму KZT в долларовый эквивалент."""
    if rate is None or rate <= 0:
        return ""
    usd = amount_kzt * rate
    return f"≈ ${usd:,.0f}".replace(",", ",") if usd >= 100 else f"≈ ${usd:,.2f}"

# ── Конфиг страницы ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Калькулятор зарплатных налогов РК 2026 | Stape",
    page_icon="🇰🇿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Стили ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .main { padding-top: 1rem; }
    h1, h2, h3 { color: #0f172a; }
    .stMetric {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
    }
    .calc-block {
        background-color: #f8fafc;
        border-left: 4px solid #2563eb;
        padding: 1rem 1.25rem;
        border-radius: 4px;
        margin-bottom: 1rem;
        font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
        font-size: 14px;
        color: #1e293b;
    }
    .calc-block b { color: #0f172a; }
    .summary-card {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    .summary-card h3 { color: white !important; margin-top: 0; }
    .summary-value { font-size: 28px; font-weight: 600; }
    .footer-note {
        font-size: 12px;
        color: #64748b;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid #e2e8f0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Функции расчёта ──────────────────────────────────────────────────────────
def fmt(value: float) -> str:
    """Форматирование суммы в тенге с разделителями."""
    return f"{value:,.0f}".replace(",", " ") + " ₸"


def calculate_taxes(
    salary: float,
    apply_deduction: bool = True,
    is_resident: bool = True,
    is_pensioner: bool = False,
    pay_opvr: bool = True,
) -> dict:
    """
    Рассчитывает все зарплатные налоги и отчисления по правилам РК 2026.

    Возвращает словарь со всеми этапами расчёта для прозрачности.
    """
    result = {"salary": salary}

    # ── Удержания с работника ────────────────────────────────────────────────

    # ОПВ — Обязательные пенсионные взносы (10%)
    # База: оклад, ограничение 50 МЗП
    # Не начисляется для пенсионеров и для иностранцев не из ЕАЭС без ВНЖ
    if is_pensioner:
        opv_base = 0
        opv = 0
        opv_note = "не начисляется (пенсионер)"
    elif not is_resident:
        opv_base = 0
        opv = 0
        opv_note = "не начисляется (нерезидент не из ЕАЭС, без ВНЖ)"
    else:
        opv_base = min(salary, OPV_BASE_CAP)
        opv = round(opv_base * 0.10)
        opv_note = (
            f"оклад × 10% = {fmt(salary)} × 10%"
            if salary <= OPV_BASE_CAP
            else f"огр. база 50 МЗП × 10% = {fmt(OPV_BASE_CAP)} × 10%"
        )
    result["opv"] = opv
    result["opv_base"] = opv_base
    result["opv_note"] = opv_note

    # ВОСМС — Взносы на ОСМС (2%)
    # База: оклад, ограничение 20 МЗП
    if is_pensioner or not is_resident:
        vosms_base = 0
        vosms = 0
        vosms_note = (
            "не начисляется (пенсионер)"
            if is_pensioner
            else "не начисляется (нерезидент без ВНЖ)"
        )
    else:
        vosms_base = min(salary, VOSMS_BASE_CAP)
        vosms = round(vosms_base * 0.02)
        vosms_note = (
            f"оклад × 2% = {fmt(salary)} × 2%"
            if salary <= VOSMS_BASE_CAP
            else f"огр. база 20 МЗП × 2% = {fmt(VOSMS_BASE_CAP)} × 2%"
        )
    result["vosms"] = vosms
    result["vosms_base"] = vosms_base
    result["vosms_note"] = vosms_note

    # ИПН — Индивидуальный подоходный налог (10%)
    # База: оклад - ОПВ - ВОСМС - вычет (30 МРП, если применяется)
    # Для нерезидентов вычет не применяется
    deduction = TAX_DEDUCTION if (apply_deduction and is_resident) else 0
    ipn_base_raw = salary - opv - vosms - deduction
    ipn_base = max(0, ipn_base_raw)

    # Прогрессия 15% на превышение порога (упрощённо, помесячно)
    if ipn_base > IPN_PROGRESSIVE_THRESHOLD_MONTH:
        ipn_normal = round(IPN_PROGRESSIVE_THRESHOLD_MONTH * 0.10)
        ipn_progressive = round(
            (ipn_base - IPN_PROGRESSIVE_THRESHOLD_MONTH) * 0.15
        )
        ipn = ipn_normal + ipn_progressive
        ipn_progressive_applied = True
    else:
        ipn = round(ipn_base * 0.10)
        ipn_progressive_applied = False

    result["deduction"] = deduction
    result["ipn_base_raw"] = ipn_base_raw
    result["ipn_base"] = ipn_base
    result["ipn"] = ipn
    result["ipn_progressive_applied"] = ipn_progressive_applied

    # На руки
    net_salary = salary - opv - vosms - ipn
    result["net_salary"] = net_salary

    # ── Платежи работодателя сверху ──────────────────────────────────────────

    # ОПВР — Обязательные пенсионные взносы работодателя (3,5%)
    # Не начисляется для пенсионеров и для иностранцев не из ЕАЭС без ВНЖ
    if pay_opvr and not is_pensioner and is_resident:
        opvr_base = min(salary, OPV_BASE_CAP)
        opvr = round(opvr_base * 0.035)
        opvr_note = f"оклад × 3,5% = {fmt(opvr_base)} × 3,5%"
    else:
        opvr = 0
        opvr_base = 0
        if is_pensioner:
            opvr_note = "не начисляется (пенсионер)"
        elif not is_resident:
            opvr_note = "не начисляется (нерезидент не из ЕАЭС, без ВНЖ)"
        else:
            opvr_note = "не начисляется"
    result["opvr"] = opvr
    result["opvr_base"] = opvr_base
    result["opvr_note"] = opvr_note

    # СО — Социальные отчисления (5%)
    # База: оклад - ОПВ, коридор 1-7 МЗП
    if is_pensioner:
        so = 0
        so_base = 0
        so_note = "не начисляется (пенсионер)"
    else:
        so_base_raw = salary - opv
        so_base = max(SO_BASE_MIN, min(so_base_raw, SO_BASE_MAX))
        so = round(so_base * 0.05)
        if so_base_raw < SO_BASE_MIN:
            so_note = f"мин. база 1 МЗП × 5% = {fmt(SO_BASE_MIN)} × 5%"
        elif so_base_raw > SO_BASE_MAX:
            so_note = f"макс. база 7 МЗП × 5% = {fmt(SO_BASE_MAX)} × 5%"
        else:
            so_note = f"(оклад − ОПВ) × 5% = {fmt(so_base)} × 5%"
    result["so"] = so
    result["so_base"] = so_base
    result["so_note"] = so_note

    # ООСМС — Отчисления на ОСМС (3%)
    # База: оклад, ограничение 40 МЗП
    if is_pensioner or not is_resident:
        oosms = 0
        oosms_base = 0
        oosms_note = (
            "не начисляется (пенсионер)"
            if is_pensioner
            else "не начисляется (нерезидент без ВНЖ)"
        )
    else:
        oosms_base = min(salary, OOSMS_BASE_CAP)
        oosms = round(oosms_base * 0.03)
        oosms_note = (
            f"оклад × 3% = {fmt(salary)} × 3%"
            if salary <= OOSMS_BASE_CAP
            else f"огр. база 40 МЗП × 3% = {fmt(OOSMS_BASE_CAP)} × 3%"
        )
    result["oosms"] = oosms
    result["oosms_base"] = oosms_base
    result["oosms_note"] = oosms_note

    # СН — Социальный налог (6%)
    # База: оклад - ОПВ - ВОСМС, минимум 14 МРП
    sn_base_raw = salary - opv - vosms
    sn_base = max(sn_base_raw, SN_BASE_MIN)
    sn = round(sn_base * 0.06)
    if sn_base_raw < SN_BASE_MIN:
        sn_note = f"мин. база 14 МРП × 6% = {fmt(SN_BASE_MIN)} × 6%"
    else:
        sn_note = f"(оклад − ОПВ − ВОСМС) × 6% = {fmt(sn_base)} × 6%"
    result["sn"] = sn
    result["sn_base"] = sn_base
    result["sn_note"] = sn_note

    # ── Итоги ────────────────────────────────────────────────────────────────
    employee_total = opv + vosms + ipn
    employer_total = opvr + so + oosms + sn
    total_cost = salary + employer_total
    result["employee_total"] = employee_total
    result["employer_total"] = employer_total
    result["total_cost"] = total_cost

    return result


# ── Сайдбар ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Параметры расчёта")

    salary = st.number_input(
        "Оклад (гросс), ₸",
        min_value=0,
        max_value=100_000_000,
        value=500_000,
        step=10_000,
        help="Сумма начисленной заработной платы до удержаний",
    )

    # Курс KZT → USD для справки
    fx = fetch_kzt_to_usd_rate()
    if fx["rate"] is not None:
        usd_value = salary * fx["rate"]
        usd_per_kzt = 1 / fx["rate"] if fx["rate"] > 0 else 0
        st.markdown(
            f"""
            <div style="
                background: #eff6ff;
                border-left: 3px solid #2563eb;
                padding: 8px 12px;
                border-radius: 4px;
                margin-top: -10px;
                margin-bottom: 12px;
                font-size: 13px;
                color: #1e40af;
            ">
                <b>≈ ${usd_value:,.2f}</b> USD<br>
                <span style="font-size: 11px; color: #64748b;">
                Курс на {fx["date"]}: $1 = {usd_per_kzt:,.2f} ₸
                </span>
            </div>
            """.replace(",", " "),
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"⚠ Курс USD недоступен ({fx['error']})")

    st.markdown("---")
    st.markdown("**Статус сотрудника**")

    is_resident = st.checkbox(
        "Резидент РК (или гражданин ЕАЭС с ВНЖ)",
        value=True,
        help=(
            "Иностранцы не из ЕАЭС и без ВНЖ не платят ОПВ, ВОСМС, ООСМС "
            "и не имеют права на стандартный вычет ИПН"
        ),
    )

    apply_deduction = st.checkbox(
        f"Применять налоговый вычет 30 МРП ({fmt(TAX_DEDUCTION)})",
        value=True,
        disabled=not is_resident,
        help=(
            "Стандартный вычет 30 МРП применяется только для резидентов "
            "по основному месту работы (требуется заявление сотрудника). "
            "Если сотрудник работает на нескольких работах, вычет применяется "
            "только на одной из них."
        ),
    )

    is_pensioner = st.checkbox(
        "Сотрудник — пенсионер",
        value=False,
        help="За пенсионеров не уплачиваются ОПВ, СО, ООСМС, ВОСМС",
    )

    pay_opvr = st.checkbox(
        "Уплачивать ОПВР",
        value=True,
        disabled=is_pensioner,
        help=(
            "ОПВР не уплачивается за сотрудников, родившихся до 01.01.1975, "
            "пенсионеров и инвалидов I-II групп"
        ),
    )

    st.markdown("---")
    st.markdown("### 📊 Справочные значения 2026")
    st.markdown(
        f"""
- **МРП:** {fmt(MRP)}
- **МЗП:** {fmt(MZP)}
- **Вычет 30 МРП:** {fmt(TAX_DEDUCTION)}
- **Лимит ОПВ (50 МЗП):** {fmt(OPV_BASE_CAP)}
- **Лимит ВОСМС (20 МЗП):** {fmt(VOSMS_BASE_CAP)}
- **Лимит ООСМС (40 МЗП):** {fmt(OOSMS_BASE_CAP)}
- **Коридор СО (1–7 МЗП):** {fmt(SO_BASE_MIN)} – {fmt(SO_BASE_MAX)}
- **Мин. база СН (14 МРП):** {fmt(SN_BASE_MIN)}
        """
    )

# ── Расчёт ───────────────────────────────────────────────────────────────────
r = calculate_taxes(
    salary=salary,
    apply_deduction=apply_deduction,
    is_resident=is_resident,
    is_pensioner=is_pensioner,
    pay_opvr=pay_opvr,
)

# ── Заголовок ────────────────────────────────────────────────────────────────
st.title("🇰🇿 Калькулятор зарплатных налогов в Казахстане")
st.markdown(
    "**Расчёт налогов и отчислений с заработной платы по законодательству РК "
    "на 2026 год.** Учитывает все актуальные изменения: новый Налоговый кодекс, "
    "повышение ОПВР до 3,5%, социальный налог 6% без вычета СО, базовый вычет "
    "30 МРП и прогрессивную шкалу ИПН."
)
st.markdown("")

# ── Сводка ───────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

# Подготовим USD-строки для карточек (если курс получен)
def _usd_line(amount_kzt: float) -> str:
    if fx["rate"] is None:
        return ""
    usd = amount_kzt * fx["rate"]
    formatted = f"${usd:,.2f}".replace(",", " ")
    return f'<div style="opacity: 0.85; margin-top: 2px; font-size: 13px;">{formatted}</div>'

with col1:
    st.markdown(
        f"""
        <div class="summary-card" style="background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);">
            <h3>💰 На руки сотруднику</h3>
            <div class="summary-value">{fmt(r["net_salary"])}</div>
            {_usd_line(r["net_salary"])}
            <div style="opacity: 0.85; margin-top: 4px;">
                {(r["net_salary"] / salary * 100) if salary else 0:.1f}% от оклада
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <div class="summary-card">
            <h3>📋 Оклад (гросс)</h3>
            <div class="summary-value">{fmt(salary)}</div>
            {_usd_line(salary)}
            <div style="opacity: 0.85; margin-top: 4px;">
                Удержания: {fmt(r["employee_total"])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <div class="summary-card" style="background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);">
            <h3>🏢 Стоимость для работодателя</h3>
            <div class="summary-value">{fmt(r["total_cost"])}</div>
            {_usd_line(r["total_cost"])}
            <div style="opacity: 0.85; margin-top: 4px;">
                Сверху оклада: {fmt(r["employer_total"])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("")

# ── Метрики ──────────────────────────────────────────────────────────────────
st.markdown("### 📈 Разбивка налогов и отчислений")

m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
m1.metric("ОПВ (10%)", fmt(r["opv"]))
m2.metric("ВОСМС (2%)", fmt(r["vosms"]))
m3.metric("ИПН (10%)", fmt(r["ipn"]))
m4.metric("ОПВР (3,5%)", fmt(r["opvr"]))
m5.metric("СО (5%)", fmt(r["so"]))
m6.metric("ООСМС (3%)", fmt(r["oosms"]))
m7.metric("СН (6%)", fmt(r["sn"]))

# ── Детальный расчёт ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🔍 Детальный пошаговый расчёт")

tab1, tab2, tab3 = st.tabs(
    ["👤 Удержания с работника", "🏢 Платежи работодателя", "📋 Итоговая таблица"]
)

with tab1:
    st.markdown("#### 1️⃣ ОПВ — Обязательные пенсионные взносы (10%)")
    st.markdown(
        f"""
        <div class="calc-block">
        <b>Формула:</b> ОПВ = оклад × 10%<br>
        <b>База:</b> {r["opv_note"]}<br>
        <b>Расчёт:</b> {fmt(r["opv_base"])} × 10% = <b>{fmt(r["opv"])}</b><br>
        <i style="color: #64748b;">Удерживается из зарплаты, перечисляется в ЕНПФ.
        База ограничена 50 МЗП ({fmt(OPV_BASE_CAP)}/мес).</i>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 2️⃣ ВОСМС — Взносы на ОСМС (2%)")
    st.markdown(
        f"""
        <div class="calc-block">
        <b>Формула:</b> ВОСМС = оклад × 2%<br>
        <b>База:</b> {r["vosms_note"]}<br>
        <b>Расчёт:</b> {fmt(r["vosms_base"])} × 2% = <b>{fmt(r["vosms"])}</b><br>
        <i style="color: #64748b;">Удерживается из зарплаты, перечисляется в ФСМС.
        База ограничена 20 МЗП ({fmt(VOSMS_BASE_CAP)}/мес), макс. взнос — 34 000 ₸.</i>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 3️⃣ ИПН — Индивидуальный подоходный налог (10%)")
    deduction_text = (
        f"<b>Налоговый вычет (30 МРП):</b> {fmt(r['deduction'])}<br>"
        if r["deduction"] > 0
        else (
            "<b>Налоговый вычет:</b> не применяется "
            f"({'нерезидент' if not is_resident else 'не подано заявление / основная работа другая'})<br>"
        )
    )
    progressive_text = ""
    if r["ipn_progressive_applied"]:
        progressive_text = (
            f"<br><b style='color:#dc2626;'>⚠ Применена прогрессивная ставка 15%</b> "
            f"на сумму превышения {fmt(IPN_PROGRESSIVE_THRESHOLD_MONTH)}/мес "
            f"(годовой порог 8 500 МРП)."
        )

    if r["ipn_base_raw"] < 0:
        ipn_calc_text = (
            f"<b>Расчёт:</b> {fmt(r['salary'])} − {fmt(r['opv'])} − "
            f"{fmt(r['vosms'])} − {fmt(r['deduction'])} = "
            f"<span style='color:#dc2626;'>{fmt(r['ipn_base_raw'])}</span> "
            f"→ база ≤ 0 → <b>ИПН = 0 ₸</b>"
        )
    else:
        ipn_calc_text = (
            f"<b>База ИПН:</b> {fmt(r['salary'])} − {fmt(r['opv'])} − "
            f"{fmt(r['vosms'])} − {fmt(r['deduction'])} = <b>{fmt(r['ipn_base'])}</b><br>"
            f"<b>Расчёт:</b> {fmt(r['ipn_base'])} × 10% = <b>{fmt(r['ipn'])}</b>"
        )

    st.markdown(
        f"""
        <div class="calc-block">
        <b>Формула:</b> ИПН = (оклад − ОПВ − вычет − ВОСМС) × 10%<br>
        {deduction_text}
        {ipn_calc_text}
        {progressive_text}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 💵 Итог: сумма «на руки»")
    st.markdown(
        f"""
        <div class="calc-block" style="border-left-color: #16a34a; background-color: #f0fdf4;">
        <b>На руки = Оклад − ОПВ − ВОСМС − ИПН</b><br>
        {fmt(r['salary'])} − {fmt(r['opv'])} − {fmt(r['vosms'])} − {fmt(r['ipn'])} =
        <b style="font-size: 18px; color: #15803d;">{fmt(r['net_salary'])}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

with tab2:
    st.markdown("#### 4️⃣ ОПВР — Обязательные пенсионные взносы работодателя (3,5%)")
    st.markdown(
        f"""
        <div class="calc-block">
        <b>Формула:</b> ОПВР = оклад × 3,5%<br>
        <b>База:</b> {r["opvr_note"]}<br>
        <b>Расчёт:</b> {fmt(r["opvr_base"])} × 3,5% = <b>{fmt(r["opvr"])}</b><br>
        <i style="color: #64748b;">Уплачивается работодателем сверх оклада.
        Не уплачивается за сотрудников, рождённых до 01.01.1975, пенсионеров и инвалидов I-II групп.
        В 2026 году ставка увеличена с 2,5% до 3,5%.</i>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 5️⃣ СО — Социальные отчисления (5%)")
    st.markdown(
        f"""
        <div class="calc-block">
        <b>Формула:</b> СО = (оклад − ОПВ) × 5%<br>
        <b>База:</b> {r["so_note"]}<br>
        <b>Расчёт:</b> {fmt(r["so_base"])} × 5% = <b>{fmt(r["so"])}</b><br>
        <i style="color: #64748b;">Уплачивается работодателем в Госфонд социального страхования.
        База в коридоре 1–7 МЗП ({fmt(SO_BASE_MIN)} – {fmt(SO_BASE_MAX)}).</i>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 6️⃣ ООСМС — Отчисления на ОСМС (3%)")
    st.markdown(
        f"""
        <div class="calc-block">
        <b>Формула:</b> ООСМС = оклад × 3%<br>
        <b>База:</b> {r["oosms_note"]}<br>
        <b>Расчёт:</b> {fmt(r["oosms_base"])} × 3% = <b>{fmt(r["oosms"])}</b><br>
        <i style="color: #64748b;">Уплачивается работодателем в ФСМС.
        База ограничена 40 МЗП ({fmt(OOSMS_BASE_CAP)}/мес).</i>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 7️⃣ СН — Социальный налог (6%)")
    st.markdown(
        f"""
        <div class="calc-block">
        <b>Формула:</b> СН = (оклад − ОПВ − ВОСМС) × 6%<br>
        <b>База:</b> {r["sn_note"]}<br>
        <b>Расчёт:</b> {fmt(r["sn_base"])} × 6% = <b>{fmt(r["sn"])}</b><br>
        <i style="color: #64748b;">Уплачивается работодателем в бюджет.
        В 2026 году взаимозачёт с СО упразднён — 6% уплачиваются полностью.
        Минимальная база — 14 МРП ({fmt(SN_BASE_MIN)}).</i>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 🏢 Итог: общая стоимость для работодателя")
    st.markdown(
        f"""
        <div class="calc-block" style="border-left-color: #dc2626; background-color: #fef2f2;">
        <b>Стоимость = Оклад + ОПВР + СО + ООСМС + СН</b><br>
        {fmt(r['salary'])} + {fmt(r['opvr'])} + {fmt(r['so'])} +
        {fmt(r['oosms'])} + {fmt(r['sn'])} =
        <b style="font-size: 18px; color: #991b1b;">{fmt(r['total_cost'])}</b><br>
        <i style="color:#64748b;">Дополнительная нагрузка сверх оклада:
        <b>{fmt(r['employer_total'])}</b>
        ({(r['employer_total'] / salary * 100) if salary else 0:.1f}% от оклада)</i>
        </div>
        """,
        unsafe_allow_html=True,
    )

with tab3:
    st.markdown("#### Сводная таблица")

    table_data = [
        {
            "Параметр": "Оклад (гросс)",
            "Сумма, ₸": fmt(r["salary"]),
            "Кто платит": "—",
            "Ставка": "—",
        },
        {
            "Параметр": "ОПВ — Обязательные пенсионные взносы",
            "Сумма, ₸": fmt(r["opv"]),
            "Кто платит": "Работник (удерж.)",
            "Ставка": "10%",
        },
        {
            "Параметр": "ВОСМС — Взносы на ОСМС",
            "Сумма, ₸": fmt(r["vosms"]),
            "Кто платит": "Работник (удерж.)",
            "Ставка": "2%",
        },
        {
            "Параметр": "ИПН — Индивидуальный подоходный налог",
            "Сумма, ₸": fmt(r["ipn"]),
            "Кто платит": "Работник (удерж.)",
            "Ставка": "10%",
        },
        {
            "Параметр": "💰 На руки",
            "Сумма, ₸": fmt(r["net_salary"]),
            "Кто платит": "—",
            "Ставка": "—",
        },
        {
            "Параметр": "ОПВР — Пенсионные взносы работодателя",
            "Сумма, ₸": fmt(r["opvr"]),
            "Кто платит": "Работодатель",
            "Ставка": "3,5%",
        },
        {
            "Параметр": "СО — Социальные отчисления",
            "Сумма, ₸": fmt(r["so"]),
            "Кто платит": "Работодатель",
            "Ставка": "5%",
        },
        {
            "Параметр": "ООСМС — Отчисления на ОСМС",
            "Сумма, ₸": fmt(r["oosms"]),
            "Кто платит": "Работодатель",
            "Ставка": "3%",
        },
        {
            "Параметр": "СН — Социальный налог",
            "Сумма, ₸": fmt(r["sn"]),
            "Кто платит": "Работодатель",
            "Ставка": "6%",
        },
        {
            "Параметр": "🏢 Общая стоимость для работодателя",
            "Сумма, ₸": fmt(r["total_cost"]),
            "Кто платит": "—",
            "Ставка": "—",
        },
    ]

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Соотношения
    st.markdown("#### 📊 Структура распределения")
    breakdown = pd.DataFrame(
        {
            "Категория": [
                "На руки сотруднику",
                "Налоги работника (ОПВ + ВОСМС + ИПН)",
                "Платежи работодателя (ОПВР + СО + ООСМС + СН)",
            ],
            "Сумма, ₸": [r["net_salary"], r["employee_total"], r["employer_total"]],
            "% от стоимости": [
                f"{(r['net_salary'] / r['total_cost'] * 100) if r['total_cost'] else 0:.1f}%",
                f"{(r['employee_total'] / r['total_cost'] * 100) if r['total_cost'] else 0:.1f}%",
                f"{(r['employer_total'] / r['total_cost'] * 100) if r['total_cost'] else 0:.1f}%",
            ],
        }
    )
    breakdown["Сумма, ₸"] = breakdown["Сумма, ₸"].apply(fmt)
    st.dataframe(breakdown, use_container_width=True, hide_index=True)

    chart_df = pd.DataFrame(
        {
            "Категория": [
                "На руки",
                "Налоги работника",
                "Платежи работодателя",
            ],
            "Сумма": [r["net_salary"], r["employee_total"], r["employer_total"]],
        }
    ).set_index("Категория")
    st.bar_chart(chart_df, color="#2563eb")

# ── Подвал ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="footer-note">
    <b>Правовая база:</b> Налоговый кодекс РК (ст. 401–437, гл. 56), Социальный кодекс РК,
    Закон РК «О республиканском бюджете на 2026–2028 годы» № 239-VIII от 10.12.2025.<br><br>
    <b>Ключевые изменения 2026 года:</b>
    <ul>
    <li>Базовый вычет увеличен с 14 МРП до 30 МРП ({fmt_html} ₸)</li>
    <li>ОПВР повышен с 2,5% до 3,5%</li>
    <li>Социальный налог зафиксирован на уровне 6% без вычета СО</li>
    <li>Введена прогрессивная шкала ИПН: 15% на годовой доход свыше 8 500 МРП</li>
    <li>Отменена корректировка 90% (КОР90)</li>
    </ul>
    Калькулятор предназначен для справочных целей. Для сложных случаев
    (несколько мест работы, инвалидность, иждивенцы, нерезиденты, ГПХ)
    обращайтесь к бухгалтеру.<br><br>
    <i>© Stape — Global Contractor Payroll · 242 локации, фиксированная плата за выплату</i>
    </div>
    """.replace("{fmt_html}", f"{TAX_DEDUCTION:,.0f}".replace(",", " ")),
    unsafe_allow_html=True,
)
