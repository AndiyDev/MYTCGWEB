# MYTCGWEB (Streamlit)

## Local run
1. Install deps: `pip install -r requirements.txt`
2. Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example`
3. Run: `streamlit run streamlit_app.py`

## Streamlit Cloud
- Set the app entrypoint to `streamlit_app.py`.
- Add DB credentials to Streamlit secrets:
```
[db]
host = "mysql-mariadb-1-25.zap-srv.com"
port = "3306"
name = "zap1010182-3"
user = "zap1010182-3"
password = "<your-password>"
```

## Assets
- Place set logos in `assets/Logos/`
- Place set symbols in `assets/Set Symbols/`
