---
title: LedgerLens API
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# LedgerLens API

The backend of LedgerLens, an AI copilot for Indian GST reconciliation: the rules engine, the two trained matchers, the money maths and the demo data (one year of books for a made-up company, with planted mistakes and an answer key).

This Space serves the API only. Health check: `/api/health`. The web app is deployed separately and calls this API.

Source: github.com/RAK2315/ledgerlens
