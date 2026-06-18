# Authentication — GECX / CX Agent Studio REST API

> Distilled from:
> https://docs.cloud.google.com/customer-engagement-ai/conversational-agents/ps/reference/authentication

## Summary

The API uses **Google Cloud OAuth 2.0 bearer tokens** — there is no simple API-key path. You obtain
a token from `gcloud` (local dev) or from Application Default Credentials (when running on GCP), and
pass it in the `Authorization` header.

## Credential options

| Context                     | Mechanism                                                                 |
|-----------------------------|---------------------------------------------------------------------------|
| Local development (a person)| User credentials via `gcloud auth application-default login`              |
| Local, testing a SA's perms | Service account **impersonation** (`roles/iam.serviceAccountTokenCreator`)|
| Running on GCP              | Attached **service account** (Compute Engine, Cloud Run, etc.) via ADC    |

## Local setup

```powershell
gcloud auth login                       # human login (console/CLI)
gcloud auth application-default login    # ADC for SDKs / local apps
gcloud config set project <PROJECT_ID>
```

## Making a request

```bash
curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "x-goog-user-project: <PROJECT_ID>" \
  "https://ces.googleapis.com/v1/projects/<PROJECT_ID>/locations/<LOCATION>/apps"
```

PowerShell equivalent:
```powershell
$token = gcloud auth print-access-token
Invoke-RestMethod -Method Get `
  -Uri "https://ces.googleapis.com/v1/projects/$ProjectId/locations/$Location/apps" `
  -Headers @{ Authorization = "Bearer $token"; "x-goog-user-project" = $ProjectId }
```

### Headers
- `Authorization: Bearer <ACCESS_TOKEN>` — **required**.
- `x-goog-user-project: <PROJECT_ID>` — sets the billing/quota project (recommended, sometimes required).

## Scopes
Not explicitly enumerated in the docs — ADC negotiates scopes based on the operation. The broad
`https://www.googleapis.com/auth/cloud-platform` scope covers these calls.

## Authorization (IAM)
Authentication ≠ authorization. After authenticating you still need IAM roles granting access to
CX Agent Studio / Conversational Agents resources on the project.

### ⚠️ To confirm
- [ ] The exact IAM role(s) needed (e.g. a Dialogflow / Conversational Agents admin or editor role).
- [ ] Which API to enable in the project (Dialogflow API / Conversational Agents API).
- [ ] Token lifetime & refresh approach for any automated scripts.

## Security notes
- Access tokens are short-lived; never commit them.
- `config/config.json` (project ids etc.) is gitignored — keep it that way.
- Prefer service-account impersonation over downloaded SA key files for automation.
