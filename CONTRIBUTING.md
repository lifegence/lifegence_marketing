# Contributing to Lifegence Marketing

Thank you for your interest in Lifegence Marketing. This guide covers the development setup and the rules for
contributions.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report vulnerabilities as described in
[SECURITY.md](SECURITY.md), not in public issues.

## 1. Before you start

- **Bugs and small fixes:** open a pull request, or an issue first if you are unsure.
- **Features and larger changes:** open an issue first and describe the goal, the input and the expected result.
- **Scope of this repository:** this is the open core: campaigns, budgets, tracking links, lead source, CSV import,
  reports and the connector framework. Connectors for specific ad platforms can be built as separate apps on top
  of the framework (see "Connector framework" in the README). Lifegence offers its own connectors on Lifegence Cloud;
  they are not part of this repository.

## 2. Developer Certificate of Origin (DCO)

All commits must be signed off. By signing off, you certify the
[Developer Certificate of Origin 1.1](https://developercertificate.org/): you wrote the change, or you otherwise
have the right to submit it under the project's license (Apache-2.0).

Add the sign-off with `git commit -s`. The name and email must match the commit author (a GitHub noreply address is
fine). The DCO check on pull requests fails otherwise; fix it with `git rebase --signoff main` and force-push. We do
not ask for a contributor license agreement (CLA).

## 3. Requirements

| Item | Version |
| --- | --- |
| Frappe Framework | v16 (`version-16` branch) |
| Python | 3.14 |
| Node.js | 24 or later |
| MariaDB | 11.8 |

We recommend the Dev Container of the official [frappe_docker](https://github.com/frappe/frappe_docker).

## 4. Setting up a development environment

```shell
bench init --frappe-branch version-16 frappe-bench
cd frappe-bench
bench new-site marketing.localhost --admin-password admin
bench get-app https://github.com/lifegence/lifegence_marketing.git
bench --site marketing.localhost install-app lifegence_marketing
bench --site marketing.localhost set-config developer_mode 1
bench --site marketing.localhost set-config allow_tests true
bench start
```

To work on the integrations, also install ERPNext, Frappe CRM or japan_workplace on a second site: the app must
work with Frappe alone and with any combination of them.

Enable pre-commit in `apps/lifegence_marketing` with `pre-commit install` (ruff, eslint and prettier).

## 5. Common commands

| Purpose | Command |
| --- | --- |
| Apply DocType changes | `bench --site marketing.localhost migrate` |
| Run all tests | `bench --site marketing.localhost run-tests --app lifegence_marketing --test-category all` |
| Run one test module | `bench --site marketing.localhost run-tests --module lifegence_marketing.marketing.doctype.marketing_import.test_marketing_import --test-category all` |
| Format and lint | `pre-commit run --all-files` |

Always pass `--test-category all`: depending on the Frappe v16 minor version, `run-tests` may otherwise skip the
integration tests.

## 6. Coding rules

- **Style:** Python is indented with tabs and follows ruff (line length 110). JavaScript follows prettier and eslint.
- **Naming:** DocType names start with `Marketing `. Field names and Select values are in English; the UI is
  translated through `translations/ja.csv`.
- **Dependencies:** Frappe is the only required app. Code for ERPNext, Frappe CRM or japan_workplace must check
  that the app is installed, and their fields are added as custom fields only when it is (see `setup.py`). Write
  the license of any new library in the pull request; it must be compatible with Apache-2.0.
- **Privacy:** the lead source cookie is first-party and server-set. Keep it minimal, and respect the consent
  setting. Never log personal data or credentials.
- **External APIs:** mock ad platform APIs in tests (record the responses), so tests do not depend on the network.
- **Secrets:** never commit API keys, tokens or passwords. Use Password fields or Frappe's Connected App.
- **Tests:** add tests for new behavior (`IntegrationTestCase` where the database is involved).

## 7. Branches, commits and pull requests

- Work on a branch in your fork, for example `feat/12-tiktok-csv` or `fix/34-budget-month`.
- Keep a pull request to one topic. The first line of a commit message is an English imperative sentence.
- Fill in the pull request template and link the issue (`Closes #12`).

## 8. Using AI coding agents

You may use AI coding agents. Read the generated code yourself and be able to explain it; give the agent only this
repository's code and synthetic data, never customer data, secrets or API keys; and do not paste code from elsewhere
without checking its license.

## 9. Language

Code, commit messages, pull requests and issues are in English. Issues and pull requests in Japanese are also
welcome.

## 10. License

Lifegence Marketing is licensed under the [Apache License 2.0](license.txt). By contributing, you agree that your
contributions are licensed under the same license.
