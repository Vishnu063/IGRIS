# Ranked business-tool assessment — Step 39

Review date: 2026-10-30. Scope: root licenses and first 75 README lines, fetched
read-only from the actual 20 upstream repositories. Git blob IDs, source URLs
and license excerpts are in `business-tool-evidence.json`; mutable default
branches are not release certifications. Root LICENSE filename guesses that
returned 404 were resolved by root directory listings. No tools installed.

Ranking assumes an initial one-person workflow/website freelancing business,
INR 0 spending and 8 GB shared RAM. It is an engineering preference, not a market
survey. Filter by an actual requirement with `business_tools.recommend` before
using rank. All deployments, hosted plans, plugins, model calls and costs need
separate verification and approval. No hosted free tier is assumed available.

| Rank | Tool | When useful | License observation / principal constraint |
|---|---|---|---|
| 1 | n8n | Workflow automation already has a local contract | Sustainable Use; internal-use limits and enterprise exclusions; client hosting/resale needs separate review |
| 2 | Activepieces | Alternative workflow automation | MIT core, separate enterprise code; choose one orchestrator |
| 3 | InvoicePlane | Simple invoices and client records | MIT-style text plus trademark restrictions; minimize customer data |
| 4 | Strapi | Website content APIs | MIT core; enterprise code excluded |
| 5 | Bagisto | Laravel commerce requirement | MIT; PHP/database stack, payment integration separate |
| 6 | Medusa | Custom commerce backend | MIT core, enterprise exceptions; README requires Node 22.22+ and PostgreSQL |
| 7 | Chatwoot | Customer support inbox | MIT core, enterprise exceptions; messaging needs client approval |
| 8 | Twenty CRM | A real CRM need | Mostly AGPLv3 plus additional permission, MIT packages, commercial enterprise files |
| 9 | Formbricks | Customer surveys | AGPLv3 core, MIT SDK/packages, enterprise exclusions; consent/privacy review |
| 10 | Plausible Analytics | Privacy-oriented analytics | AGPLv3 root; evaluate community distribution separately |
| 11 | Appsmith | Internal admin applications | Apache-2.0 root; edition and connector review still needed |
| 12 | Budibase | Internal operations apps | GPLv3 overall, MPL app packages, BSL paid features; do not bypass license checks |
| 13 | Odoo | Several integrated business processes | LGPLv3 community; enterprise/apps have separate terms |
| 14 | ERPNext | Established ERP requirement | GPLv3 root; defer until operational complexity warrants it |
| 15 | Saleor | GraphQL commerce requirement | BSD-3-Clause; full commerce stack is unnecessary initially |
| 16 | Coolify | Approved remote hosting operations | Apache-2.0 root; SSH/server authority, remote resources and cost required |
| 17 | Mautic | Consented marketing automation | GPLv3-or-later; email delivery/consent/cost separate |
| 18 | Directus | SQL-backed APIs and studio | Actual current license MSCL-1.0-GPL; competing-use and license-key limits, eligibility review needed |
| 19 | NocoDB | Spreadsheet-style database UI | Actual current Sustainable Use license on master/develop; other branches unlicensed per notice |
| 20 | Akaunting | Accounting beyond local ledger | BSL-1.1: production grant limits users/company/invoices and accounting-service use; four-year version-specific change |

For planning only, reserve roughly 0.5–2 GiB for one small web/PHP service plus
database, 1–3 GiB for a small workflow service, and 2–6+ GiB for a multi-service
CRM/commerce/ERP/analytics stack. These broad estimates are **unmeasured**, not
vendor minimums. Build peaks, Docker VM overhead, databases, media and the OS can
exceed them. Apple Silicon images and 50 GB total storage remain unverified for
every tool. Do not run these stacks alongside large local speech/models on 8 GB.

Only the previously tested n8n local contract adapter exists. No additional
adapter is authorized or implemented here. A zero-service local business ledger
and generated client project remain the lowest-resource starting point.
