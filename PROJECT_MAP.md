# 🗺️ PROJECT NAVIGATION MAP

## 📍 Where to Find Things

### 🎯 Start Here
- **Current Status**: `docs/state/SYSTEM_STATE.md`
- **Architecture**: `docs/architecture/ARCHITECTURE.md`
- **Dev Rules**: `docs/architecture/DEVELOPMENT_RULES.md`

### 📁 Directory Purpose Guide

```
hormozi_rag/
├── api/          → HTTP endpoints, request handling
├── config/       → Settings, environment variables
├── core/         → Business logic, orchestration
├── embeddings/   → Text → Vector conversion
├── extractors/   → PDF → Text extraction
├── retrieval/    → Vector search, ranking
└── tests/        → All test files

data/
├── raw/          → Original PDF files
├── processed/    → Chunked text documents
└── embeddings/   → Vector representations

docs/
├── architecture/ → System design docs
├── decisions/    → Why we built it this way
└── state/        → Current implementation status

scripts/
├── validation/   → Code quality checks
└── setup/        → Installation, deployment
```

## 🔄 Common Workflows

### 1️⃣ "I want to add a new feature"
```bash
1. cat docs/architecture/ARCHITECTURE.md
2. Check if it fits the design
3. Update docs first if needed
4. Implement in correct module
5. Run validation scripts
```

### 2️⃣ "Something is broken"
```bash
1. cat docs/state/SYSTEM_STATE.md
2. Check "Current Issues" section
3. Find root cause (not symptom)
4. Fix in appropriate module
5. Update system state
```

### 3️⃣ "I need to understand the code"
```bash
1. Start with ARCHITECTURE.md
2. Check module responsibilities
3. Follow data flow diagram
4. Read specific module code
```

## 📝 File Naming Conventions

- **Python modules**: `snake_case.py`
- **Documentation**: `UPPER_CASE.md` (important) or `kebab-case.md`
- **Config files**: `.lowercase` or `lowercase.yaml`
- **Test files**: `test_*.py`

## 🏷️ Quick Reference

| Need | Location |
|------|----------|
| API endpoints | `hormozi_rag/api/app.py` |
| Database config | `hormozi_rag/config/settings.py` |
| PDF processing | `hormozi_rag/extractors/pdf_extractor.py` |
| Vector search | `hormozi_rag/retrieval/retriever.py` |
| Main orchestration | `hormozi_rag/core/orchestrator.py` |
| Environment vars | `.env` (create from `.env.example`) |

## 🚦 Status Indicators

- ✅ **Complete**: Module fully implemented and tested
- 🚧 **In Progress**: Partially implemented
- ❌ **Not Started**: Placeholder or not implemented
- ⚠️ **Has Issues**: Working but needs fixes

## 🔍 Search Patterns

Find all TODOs:
```bash
grep -r "TODO" hormozi_rag/
```

Find hardcoded values:
```bash
python scripts/validation/check_hardcoding.py
```

Find complex functions:
```bash
python scripts/validation/check_complexity.py
```

## 📊 Metrics Locations

- **Code metrics**: Run `update_system_state.py`
- **Test coverage**: Run `pytest --cov`
- **Performance**: Check `SYSTEM_STATE.md` benchmarks
- **API metrics**: `/metrics` endpoint (when running)