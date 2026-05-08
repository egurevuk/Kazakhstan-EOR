# Kazakhstan Salary Tax Calculator 2026

Streamlit calculator for Kazakhstan payroll taxes — employee deductions, employer payments, and take-home pay under 2026 tax law. RU / EN bilingual.

🔗 **Live demo:** [your-streamlit-url-here]

## Features

- All seven 2026 taxes: ОПВ, ВОСМС, ИПН, ОПВР, СО, ООСМС, СН
- Correct base caps and corridors (50 МЗП, 20 МЗП, 1–7 МЗП, 14 МРП, etc.)
- 30 МРП standard deduction toggle
- Resident vs. non-resident treatment (Art. 692 НК РК)
- Pensioner mode
- USD reference via exchangeratesapi.io
- Stape brand design

## Quick start

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your exchangeratesapi.io key
streamlit run kz_tax_calculator.py
```

## Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app → select repo
3. Main file: `kz_tax_calculator.py`
4. App settings → Secrets → paste:
```toml
   EXCHANGERATES_API_KEY = "your_key_here"
```

## Legal basis

Tax Code of Kazakhstan (art. 401–437, ch. 56) · Social Code · Law of RK "On the Republican Budget for 2026–2028" № 239-VIII of 10.12.2025.

For reference only. For complex cases (multiple jobs, disability, dependants, GPH contracts), consult an accountant.

---

Built by Stape — Global Contractor Payroll · 242 locations, flat fee per payout.
