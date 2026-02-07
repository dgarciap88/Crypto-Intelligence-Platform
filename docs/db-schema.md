
---

## 📄 3️⃣ `db-schema.md`
```markdown
# Database Schema - CIP

## Tablas principales

### Projects
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    token_symbol TEXT,
    created_at TIMESTAMP DEFAULT now()
);
