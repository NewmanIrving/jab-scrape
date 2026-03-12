# job_scrape

MVP FastAPI 工程骨架（Story 1.1）

## 环境要求

- Python 3.11+

## 安装

```sh
python -m pip install -e ".[dev]"
```

## 本地运行

```sh
uvicorn app.main:app --reload
```

## 健康检查

```sh
curl http://127.0.0.1:8000/health
```

期望返回：

```json
{"status":"ok"}
```

## 数据库迁移（Alembic）

```sh
alembic upgrade head
```

## 质量门禁

```sh
ruff check .
pytest
```

## 最小目录结构

- app/main.py
- app/api/
- app/core/
- app/db/
- tests/
- alembic/
- alembic.ini
- pyproject.toml
- .env.example
