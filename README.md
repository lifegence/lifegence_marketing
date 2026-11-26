# Lifegence Marketing

Advertising and campaign management for [Frappe](https://frappe.io): campaigns with budgets by channel and month,
tracking links with UTM parameters, ad performance, and the cost of leads, deals and revenue.

Part of [Lifegence Cloud](https://lifegence.com). This repository is the open core (Apache-2.0). Media connectors
that import ad performance through the channels' APIs (Meta, Google, ChatGPT and others) and AI skills are offered
separately on Lifegence Cloud.

> Status: early development (phase 1, weeks 1 to 6 of about 6 to 8: campaigns, budgets, channels, ad accounts,
> tracking links, the source of leads, CSV import of ad performance, reports, and the connector framework).

## Features (phase 1)

| Area | What it does |
|---|---|
| Campaigns | Objective, period, owner, targets (leads, cost per lead, ROAS) and a budget by channel and month. The campaign code is the UTM campaign shared with leads, deals and orders |
| Channels and ad accounts | Social, search, display, conversational AI (ChatGPT), offline. Ad accounts per channel |
| Tracking links | Destination URL with UTM parameters, a short URL (`/m/<code>`) that counts clicks, and a QR code |
| Lead source | A website visit with UTM parameters or click IDs (gclid, fbclid, ...) sets a first-party cookie (first and last touch). When the visitor becomes a lead (ERPNext Lead or Frappe CRM CRM Lead, for example from a web form), the lead gets its UTM fields and a Marketing Attribution record. Only UTM values that already exist fill the lead fields; others are kept as text. Optional consent cookie |
| Lead ads | Leads from Meta lead forms (Frappe CRM) get their campaign from a form-to-campaign map. Frappe CRM deals take the UTM fields and campaign of their lead |
| Ad performance (CSV) | Import a channel's CSV export (UTF-8 or Shift_JIS; common English and Japanese headers are recognised, a profile names others). Daily figures by ad and placement; importing a period again replaces it. The channel's campaigns, ad groups and ads are matched to a campaign by the campaign code at the start of their name, or by hand |
| Reports | Campaign Performance (budget, cost, impressions, clicks, leads, cost per lead, deals, deal rate, won, revenue, ROAS; by campaign, channel or both; first or last touch), Budget vs Actual (by campaign, channel and month, with the forecast for the current month), Channel Summary (monthly trend), Ad Spend Reconciliation (channel-reported cost against purchase invoices, ERPNext) |
| Approval | Optionally requires a decided ringi (japan_workplace) before a campaign becomes Active; a Create Ringi button fills in the ringi, and the campaign owner is notified when it is decided |

## Connector framework

Connectors import ad performance (and lead form leads) through the channels' APIs every day. A connector app
registers them in its `hooks.py`:

```python
marketing_connectors = {"meta": "my_app.meta.MetaConnector"}
```

and implements `lifegence_marketing.connectors.base.MarketingConnector` (`test_connection`, `fetch_performance`,
optionally `fetch_leads`), returning plain dicts. The framework fetches the last 7 days on every run (90 days the
first time), writes the figures, creates leads, keeps a Marketing Sync Log, notifies Marketing Managers of failures
and retries up to three times a day. OAuth tokens come from Frappe's Connected App.

## Requirements

- Frappe v16. That is the only required app.
- Optional: ERPNext (company, cost center, project, supplier, purchase invoice reconciliation),
  Frappe CRM (UTM fields on CRM Lead and CRM Deal), japan_workplace (approval by ringi). Their fields are added only
  when the app is installed, also when it is installed later.

## Installation

```bash
bench get-app https://github.com/lifegence/lifegence_marketing
bench --site <site> install-app lifegence_marketing
```

## Tests

```bash
bench --site <test site> set-config allow_tests true
bench --site <test site> run-tests --app lifegence_marketing
```

## License

Apache-2.0. See [license.txt](license.txt).
