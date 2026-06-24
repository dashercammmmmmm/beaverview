# BeaverView Azure/Entra App Registration Checklist

Use this checklist when an OSU admin is ready to create the Entra SSO app.

## App Registration

| Field | Value |
|---|---|
| Name | `BeaverView` |
| Supported account types | Accounts in this organizational directory only |
| Platform | Web |
| Redirect URI | `https://beaverview/auth/callback` |
| Logout redirect URI | `https://beaverview/` |

The redirect URI must match exactly. Do not add a trailing slash to `/auth/callback`.

## API Permissions

Microsoft Graph delegated permissions:

- `openid`
- `profile`
- `email`
- `User.Read`

If group claims are not present in the ID token, configure token group claims or Graph access according to OSU Entra policy.

## Client Secret

Create a client secret under **Certificates & secrets** and copy the **Value** immediately. The value cannot be recovered later.

## Security Groups

Create or identify:

- `BeaverView Technicians`
- `BeaverView Admins`

Copy each group **Object ID** for `api/.env`.

## api/.env Values

```bash
AZURE_TENANT_ID=<Directory tenant ID>
AZURE_CLIENT_ID=<Application client ID>
AZURE_CLIENT_SECRET=<Client secret value>
AZURE_REDIRECT_URI=https://beaverview/auth/callback
AZURE_GROUP_TECHNICIAN=<Technicians group object ID>
AZURE_GROUP_ADMIN=<Admins group object ID>
```

After updating `api/.env`, restart BeaverView and run:

```bash
python3 scripts/check_pilot_readiness.py
```
