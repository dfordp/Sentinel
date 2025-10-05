```bash
docker run -d --name pgvector-db -e POSTGRES_PASSWORD=yourpassword -p 5432:5432 ankane/pgvector
```
```bash
docker exec -it pgvector-db psql -U postgres
```

```bash
CREATE EXTENSION IF NOT EXISTS vector;
```

```bash
CREATE TABLE github_items (
  id BIGINT PRIMARY KEY,
  number INTEGER,
  type TEXT,
  keywords TEXT[],
  labels TEXT[],
  comments TEXT[],
  embedding VECTOR(1536),
  state TEXT,
  author TEXT,
  updated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ,
  related TEXT[],
  is_stale BOOLEAN,
  is_spam BOOLEAN,
  matches_requirements BOOLEAN,
  title TEXT,
  body TEXT,
  file_urls TEXT[],
  diff_summary TEXT
);
```