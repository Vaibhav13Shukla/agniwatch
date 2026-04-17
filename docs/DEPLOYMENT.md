# AGNIWATCH Deployment Guide

## 1. Streamlit Community Cloud

1. Push this repository to GitHub.
2. Open https://share.streamlit.io and create a new app.
3. Select `streamlit_app.py` as entrypoint.

## 2. Configure Secrets

In Streamlit app settings, add secrets:

```toml
[gee]
service_account = "agniwatch@your-project.iam.gserviceaccount.com"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

Alternative for local/CI:
- `GEE_PROJECT`
- `GEE_SERVICE_ACCOUNT_JSON`

## 3. Validate Deployment

1. Open app and verify Demo mode loads.
2. Set `GEE_PROJECT`, switch to Live mode.
3. Run one region/year and check:
   - KPIs populate
   - Alert JSON download works
   - CSV export works

## 4. Security Notes

- Never commit `.streamlit/secrets.toml`.
- Use app passwords for SMTP; never use account passwords.
- Rotate service account keys periodically.

## 5. Optional GitHub Actions

The included workflow runs basic Python checks and tests on push/PR.
