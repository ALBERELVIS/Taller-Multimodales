CSS = """
<style>
    .stApp { background: #0E1420; }
    header[data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: #121A28; border-right: 1px solid #2E3A4F; }
    .hero { padding: 0.2rem 0 1rem 0; }
    .kicker {
        color: #E0B15A; letter-spacing: 0.16em; font-size: 0.78rem;
        font-weight: 700; margin-bottom: 0.35rem;
    }
    .hero h1 { font-size: 3rem; line-height: 1; margin: 0; color: #F4F1EA; font-weight: 700; }
    .hero p { color: #9AA4B2; font-size: 1.05rem; margin: 0.45rem 0 0 0; max-width: 42rem; }
    .stance {
        display: inline-block; background: #E0B15A; color: #0E1420;
        font-weight: 700; border-radius: 999px; padding: 0.25rem 0.8rem; margin-top: 0.6rem;
    }
    .note { color: #9AA4B2; font-size: 0.92rem; }
    .panel {
        background: #182232; border: 1px solid #2E3A4F; border-radius: 16px;
        padding: 0.9rem 1rem; margin: 0.4rem 0 0.8rem 0;
    }
    .kpi-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 0.8rem 0 1rem 0; }
    .kpi { background: #182232; border: 1px solid #2E3A4F; border-radius: 16px; padding: 0.75rem 0.9rem; }
    .kpi span { color: #9AA4B2; font-size: 0.82rem; }
    .kpi strong { display: block; color: #F4F1EA; font-size: 1.45rem; margin-top: 0.25rem; font-weight: 700; }
</style>
"""
