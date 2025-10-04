# 🚨 PR Sentinel (MVP)

PR Sentinel is a GitHub App designed to help **open source maintainers and teams** cut through the noise in their repositories.
Instead of just code review, PR Sentinel focuses on **community health, contribution quality, and actionable signals** so maintainers can spend less time filtering spam or duplicates — and more time merging meaningful work.

---

## ✨ What It Does (MVP)

In this MVP version, PR Sentinel provides a simple but powerful workflow:

1. **Load a Repository**

   * Select a repo and trigger a background job to sync its open PRs and issues.

2. **Embed Contributions with pgvector**

   * PRs and issues are stored in PostgreSQL with vector embeddings (via pgvector) for semantic search.

3. **Surface Insights**

   * For each PR, PR Sentinel shows:

     * **Similar past PRs or issues** (to catch duplicates or related work).
     * **Contributor context** (new vs returning).
     * **Simple signals** like missing linked issue or suspiciously low-effort descriptions.

4. **Temporary Workspace**

   * Repositories can be loaded and unloaded dynamically.
   * Data is cleaned up after the session/demo, so the system stays lean.

---

## 🧩 Why It Matters

Maintainers of popular repos face three key challenges:

* **Noise**: Spam PRs, duplicates, or trivial contributions.
* **Context switching**: Hard to track if a new PR relates to older issues or previous attempts.
* **Time pressure**: Limited time to triage community contributions.

PR Sentinel addresses these by:

* **Embedding repo context** (via pgvector) so PRs/issues can be matched semantically.
* **Highlighting contributor activity** (new vs repeat).
* **Providing actionable signals** at a glance.

This makes it easier to decide: **merge, request changes, or close**.

---

## ⚙️ Technical Overview (MVP)

* **Backend**: FastAPI (receives GitHub webhooks, exposes APIs).
* **Frontend**: Next.js + Tailwind (dashboard for maintainers).
* **Database**: PostgreSQL with `pgvector` (hosted via Supabase or Docker).
* **Background Tasks**: Workers to fetch data, generate embeddings, and clean up after use.
* **Auth**: GitHub App installation flow (repo-scoped).

### Data Flow

1. Maintainer installs GitHub App.
2. Webhook → Backend → Enqueue “Load Repo” task.
3. Worker fetches PRs/issues, generates embeddings, stores in Postgres.
4. Frontend queries backend for PR insights (similar PRs/issues, contributor history).
5. Cleanup process deletes embeddings when repo/session ends.

---

## 🛠️ Features in MVP

* [x] GitHub App integration
* [x] Background task to load and embed repos
* [x] Store embeddings in Postgres/pgvector
* [x] Query API for “similar PRs/issues”
* [x] Cleanup endpoints to remove repo data
* [ ] Polished maintainer dashboard

---

## 🚀 Future Roadmap

The MVP lays the foundation for more advanced capabilities:

* AI-powered PR classification (spam/duplicate/valuable).
* Contributor reputation and trust scoring.
* Community health analytics (trends, bottlenecks).
* Multi-repo governance dashboards.
* Extensible knowledge graph for long-term history.

---

## 📦 Deployment

* **Local**: Docker Compose (backend, frontend, Postgres).
* **Cloud**: Supabase (Postgres + pgvector), Railway/Fly.io for backend, Vercel for frontend.
* **Cleanup**: Automatic expiration of repo data after demo sessions.

---

## 🎯 Target Users

* Open source maintainers
* Community managers
* Engineering orgs that manage external contributions


