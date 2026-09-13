# API Reference

Base path: `/api`. Interactive docs (Swagger UI) at `/docs`; OpenAPI at
`/api/openapi.json`. All endpoints return JSON. The API is authentication-ready:
set `API_KEY` to require an `X-API-Key` header (unset in the demo).

## System
| Method | Path | Description |
|------|------|-------------|
| GET | `/api/health` | Liveness + DB connectivity |

## Students & risk
| Method | Path | Description |
|------|------|-------------|
| GET | `/api/students` | Paginated list (`search`, `program`) |
| POST | `/api/students` | Create a student |
| GET | `/api/students/{id}` | Student record |
| GET | `/api/students/at-risk` | Students ranked by risk (`label`, `limit`) |
| GET | `/api/students/{id}/risk` | Risk label, probability, SHAP factors, NL explanation |
| GET | `/api/students/{id}/trajectory` | Score/attendance/mastery series + risk trajectory |
| GET | `/api/students/{id}/recommendations` | Weakness-keyed intervention recommendations |

## Courses & topics
| Method | Path | Description |
|------|------|-------------|
| GET | `/api/courses` | List courses |
| GET | `/api/courses/{id}` | Course record |
| GET | `/api/courses/{id}/topics` | Topics in a course |
| GET | `/api/courses/{id}/health` | Transparent health score + components + weights |
| GET | `/api/courses/{id}/topics/performance` | Topic mastery for a course |
| GET | `/api/topics/weak` | Weakest topics platform-wide |
| GET | `/api/topics/{id}/performance` | Topic mastery, distribution, weak flag |
| GET | `/api/topics/{id}/students` | Per-student mastery (drilldown) |

## Feedback (NLP)
| Method | Path | Description |
|------|------|-------------|
| GET | `/api/feedback/insights` | Sentiment, top issues, topic-level sentiment |
| POST | `/api/feedback/analyze` | Analyse one feedback text (`method`: rule/transformer/llm) |
| GET | `/api/feedback/method-comparison` | Accuracy of the three methods vs ratings |

## Analytics
| Method | Path | Description |
|------|------|-------------|
| GET | `/api/dashboard/overview` | Executive KPIs, trend, risk, alerts, insights |
| GET | `/api/analytics/anomalies` | Isolation-Forest + z-score anomalies |
| GET | `/api/analytics/data-quality` | Data-quality report |
| GET | `/api/analytics/business-insights` | Computed NL business insights |

## RAG & documents
| Method | Path | Description |
|------|------|-------------|
| GET | `/api/documents` | List ingested documents |
| POST | `/api/documents/upload` | Upload a PDF/text file (multipart) |
| POST | `/api/documents/text` | Ingest raw text |
| POST | `/api/rag/query` | Semantic search with metadata filters + citations |

## AI Analyst & reports
| Method | Path | Description |
|------|------|-------------|
| POST | `/api/analyst/query` | Grounded, cited answer (or insufficient) |
| GET | `/api/reports/weekly` | Automated Education Intelligence Report |

## Interventions
| Method | Path | Description |
|------|------|-------------|
| GET | `/api/interventions` | List (filter by `student_id`) |
| POST | `/api/interventions` | Record an intervention |
| POST | `/api/interventions/{id}/outcome` | Record a before/after outcome |
| GET | `/api/interventions/effectiveness` | Aggregate effectiveness (+ non-causal caveat) |

## ML lifecycle
| Method | Path | Description |
|------|------|-------------|
| GET | `/api/models` | Model versions + metric summaries |
| GET | `/api/models/{id}` | Full metrics, hyperparameters |
| GET | `/api/experiments` | Training runs |
| GET | `/api/experiments/{id}` | Full experiment detail |
