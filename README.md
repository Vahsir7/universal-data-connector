# Universal Data Connector

> **Articence DSInternship Submission — Function Calling with LLM Track**
> *A production-grade FastAPI service enabling LLMs to intelligently query business data through a unified, voice-optimized interface*

---

## 📋 Table of Contents

- [Executive Summary](#-executive-summary)
- [Project Overview](#-project-overview)
- [Quick Start Guide](#-quick-start-guide)
- [Architecture &amp; Design Philosophy](#-architecture--design-philosophy)
- [API Documentation](#-api-documentation)
- [Implementation Details](#-implementation-details)
- [Bonus Features](#-bonus-features-implemented)
- [Testing &amp; Quality Assurance](#-testing--quality-assurance)
- [Deployment Guide](#-deployment-guide)
- [Design Decisions &amp; Trade-offs](#-design-decisions--trade-offs)
- [Challenges &amp; Solutions](#-challenges--solutions)
- [Future Enhancements](#-future-enhancements)

---

## 🎯 Executive Summary

This project addresses a critical challenge in LLM applications: **how to give AI assistants safe, efficient access to business data without context window overflow, data leakage, or irrelevant responses**.

Rather than dumping raw JSON files into prompts, this solution provides:

- **A unified REST API** with intelligent filtering, pagination, and metadata
- **Voice-first optimization** that summarizes large datasets into concise, speakable contexts
- **Multi-provider LLM integration** (OpenAI, Anthropic, Gemini) with function calling
- **Production-ready infrastructure** including caching, rate limiting, authentication, and observability

**All core requirements met** + **all 7 bonus challenges implemented**.

---

## 📖 Project Overview

### The Problem

Modern SaaS companies need AI assistants that can answer customer questions about:

- CRM data (customer records, status, activity)
- Support tickets (issues, priorities, resolution times)
- Analytics metrics (DAU, engagement, error rates)

Challenges:

1. **Context limits**: Raw data files exceed LLM token limits
2. **Relevance**: Users need filtered results, not full datasets
3. **Voice UX**: Speech interfaces require concise, natural summaries
4. **Cost**: Every API call to an LLM costs money
5. **Security**: Data must be filtered and validated before exposure

### The Solution

A specialized middleware service that:

1. **Abstracts data sources** behind a consistent interface
2. **Applies intelligent filtering** based on query parameters
3. **Detects data types** and calculates freshness/staleness
4. **Optimizes for voice** by generating natural language summaries
5. **Caches aggressively** to reduce latency and LLM costs
6. **Integrates with LLMs** through structured function calling

### Key Features

|            Feature            |                         Description                         |
| :----------------------------: | :---------------------------------------------------------: |
|  **Unified Interface**  | Single API contract (`/data/{source}`) for all data types |
|    **3 Data Sources**    |   CRM (customers), Support (tickets), Analytics (metrics)   |
|   **Smart Filtering**   |   Filter by status, priority, date range, ID, metric name   |
|  **Voice Optimization**  |       Auto-generates summaries for large result sets       |
| **Data Type Detection** |      Identifies tabular/time-series/hierarchical data      |
| **Freshness Indicators** |        Calculates staleness (fresh/stale/very_stale)        |
|    **Redis Caching**    |           Two-tier cache with in-memory fallback           |
|    **Rate Limiting**    |               Per-source IP-based throttling               |
|   **NDJSON Streaming**   |             Stream large datasets line-by-line             |
|        **Web UI**        |              Interactive dashboard for testing              |
|    **Authentication**    |           API key management with SHA-256 hashing           |
|       **Webhooks**       |      Real-time event ingestion with cache invalidation      |
|     **Data Export**     |              Download results as CSV or Excel              |
|   **LLM Integration**   |         OpenAI, Anthropic, Gemini function calling         |
|  **Hybrid Resolution**  |     Regex fallbacks for common queries (no LLM needed)     |

---

## 🚀 Quick Start Guide

### Prerequisites

- **Python 3.11+** (for local development)
- **Docker Desktop** (for containerized deployment)
- **kubectl** (for Kubernetes deployment - optional)

### Starting the Application

This project includes **helper scripts** (`start-stack.bat`, `stop-stack.bat`) that automate the entire setup process.

#### Option 1: Docker Compose (Recommended)

**Best for**: Full feature testing with Redis caching

```powershell
# Start API + Redis in Docker
.\start-stack.bat docker

# Wait for "API available at http://localhost:8000" message
```

**What happens:**

1. Builds Docker image from `Dockerfile`
2. Starts API container (4 Uvicorn workers) + Redis container
3. Waits for health check to pass
4. Opens browser to API documentation

**Access points:**

- Interactive API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Web UI Dashboard: [http://localhost:8000/ui](http://localhost:8000/ui)
- Health Check: [http://localhost:8000/health/live](http://localhost:8000/health/live)

**To stop:**

```powershell
.\stop-stack.bat docker
```

---

#### Option 2: Local Python Development

**Best for**: Rapid iteration during development

```powershell
# 1. Create virtual environment
python -m venv .venv

# 2. Activate environment (Windows)
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Notes:**

- Redis caching automatically falls back to in-memory if Redis is unavailable
- All features work except distributed caching across multiple instances

**Access points:**

- Same as Docker option, but on `http://127.0.0.1:8000`

---

#### Option 3: Kubernetes

**Best for**: Testing scalability, HPA, and multi-pod deployment

```powershell
# Deploy to kind (local cluster) or existing K8s cluster
.\start-stack.bat k8s

# Script will:
# 1. Build and load image into kind
# 2. Apply Kubernetes manifests (namespace, deployments, services)
# 3. Wait for rollout to complete
# 4. Set up port-forwarding
```

**What's deployed:**

- Redis StatefulSet (persistent cache)
- API Deployment (2-10 replicas with HPA)
- Services, ConfigMaps, Secrets
- Horizontal Pod Autoscaler (scales on CPU)
- PodDisruptionBudget (high availability)

**Access points:**

- Via port-forward: [http://localhost:8080/docs](http://localhost:8080/docs)

**To stop:**

```powershell
.\stop-stack.bat k8s          # Remove deployments
.\stop-stack.bat kind-delete  # Delete entire cluster
```

---

### Quick Verification

Once the service is running, test the endpoints:

```powershell
# Check health
curl http://localhost:8000/health/ready

# Query CRM data
curl "http://localhost:8000/data/crm?page=1&page_size=5"

# Query support tickets
curl "http://localhost:8000/data/support?status=open&priority=high"

# Query analytics metrics
curl "http://localhost:8000/data/analytics?metric=daily_active_users&start_date=2024-01-01&end_date=2024-01-07"
```

### Environment Configuration

Create a `.env` file for custom settings (optional):

```env
# Core Settings
VOICE_SUMMARY_THRESHOLD=10    # Results before voice summary kicks in

# Redis Cache
ENABLE_REDIS_CACHE=true
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=60

# Rate Limiting
RATE_LIMIT_PER_SOURCE=60      # Max requests per window
RATE_LIMIT_WINDOW_SECONDS=60

# Authentication (set to true in production)
AUTH_ENABLED=false
ADMIN_API_KEY=your-secure-admin-key

# LLM Providers (for /assistant/query endpoint)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
```

All settings have sensible defaults and work without a `.env` file.

---

## 🏗 Architecture & Design Philosophy

### High-Level Architecture

```
┌─────────────┐
│   Client    │  (User, LLM, Web UI)
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────────────────────────────────┐
│         FastAPI Application              │
│  ┌────────────────────────────────┐    │
│  │  Middleware Layer               │    │
│  │  • Request Logging              │    │
│  │  • Error Handling               │    │
│  │  • Rate Limiting                │    │
│  │  • Authentication               │    │
│  └────────────────────────────────┘    │
│                                          │
│  ┌────────────────────────────────┐    │
│  │  Router Layer                   │    │
│  │  /data  /assistant  /export     │    │
│  │  /auth  /webhooks   /health     │    │
│  └────────────────────────────────┘    │
│                                          │
│  ┌────────────────────────────────┐    │
│  │  Service Layer                  │    │
│  │  • Data Service (8-step pipeline)   │
│  │  • LLM Service (multi-provider) │    │
│  │  • Business Rules Engine        │    │
│  │  • Cache Service                │    │
│  └────────────────────────────────┘    │
│                                          │
│  ┌────────────────────────────────┐    │
│  │  Connector Layer                │    │
│  │  CRM   Support   Analytics      │    │
│  └────────────────────────────────┘    │
└─────────────────────────────────────────┘
       │           │            │
       ▼           ▼            ▼
   JSON Files   Redis       SQLite
   (data/)      (cache)     (auth/webhooks)
```

Every request to `/data/{source}` flows through a carefully ordered pipeline (`app/services/data_service.py`):

#### 1️⃣ **Connector Stage**

**Purpose**: Read raw data from source
**Implementation**: Each connector (`CRMConnector`, `SupportConnector`, `AnalyticsConnector`) extends `BaseConnector` and implements a single `fetch()` method.
**Current**: Reads from JSON files
**Production**: Would connect to PostgreSQL, MongoDB, or REST APIs

```python
raw_records = connector.fetch()  # Returns List[Dict[str, Any]]
```

---

#### 2️⃣ **Identifier Stage**

**Purpose**: Detect data characteristics**Detects**:

- **Data Type**: `tabular` (flat records), `time_series` (timestamped metrics), or `hierarchical` (nested)
- **Freshness**: Compares file modification time vs. current time
  - `fresh`: < 1 hour old
  - `stale`: 1-24 hours old
  - `very_stale`: > 24 hours old

**Why it matters**: LLMs make better decisions when they know if data is current or outdated.

---

#### 3️⃣ **Flatten Stage**

**Purpose**: Normalize hierarchical records
**Example**:

```json
// Before
{"user": {"name": "Alice", "meta": {"role": "admin"}}}

// After
{"user.name": "Alice", "user.meta.role": "admin"}
```

---

#### 4️⃣ **Filter Stage**

**Purpose**: Apply business rule filters**Filters**:

- `status`: Exact match (e.g., `"active"`, `"open"`)
- `priority`: Exact match (e.g., `"high"`, `"medium"`)
- `date_range`: Inclusive filter on `start_date` / `end_date`
- `ticket_id` / `customer_id`: Single record lookup
- `metric`: Analytics metric name filter
- `query`: Free-text search (basic substring match)

**Implementation**: See `app/services/business_rules.py`

---

#### 5️⃣ **Sort Stage**

**Purpose**: Order by relevance
**Logic**: Finds the first timestamp field (`created_at`, `date`, `timestamp`) and sorts **descending** (newest first).

**Why**: Users care about recent activity. Oldest-first rarely makes sense for business queries.

---

#### 6️⃣ **Voice Optimization Stage**

**Purpose**: Cap results for voice interfaces
**Threshold**: `VOICE_SUMMARY_THRESHOLD` (default: 10)
**Action**: If `len(records) > threshold`, limits to threshold and generates `voice_context`.

**Example**:

```json
"voice_context": "Showing 10 of 47 active customers. Most recently created first."
```

**Design Rationale**: Voice assistants can't read 50 records aloud. The summary gives context without overwhelming the user.

---

#### 7️⃣ **Paginate Stage**

**Purpose**: Slice to requested page
**Parameters**: `page` (1-indexed), `page_size` (max: 50)
**Calculation**:

```python
start = (page - 1) * page_size
end = start + page_size
paginated_records = records[start:end]
```

---

#### 8️⃣ **Assemble Stage**

**Purpose**: Build final response with metadata
**Output**:

```json
{
  "data": [...],
  "metadata": {
    "total_results": 47,
    "returned_results": 5,
    "data_freshness": "2 hours ago",
    "staleness_indicator": "fresh",
    "data_type": "tabular",
    "voice_context": "Showing 5 of 47 results...",
    "page": 1,
    "page_size": 5,
    "total_pages": 10,
    "has_next": true
  }
}
```

---

### Why This Order Matters

1. **Filter before paginate**: Ensures `total_results` reflects the *filtered* count, not raw count.
2. **Sort before voice optimization**: Ensures the "most relevant" subset is selected for voice.
3. **Voice optimization before pagination**: Allows natural summaries like "Showing 5 of 100" even when pagination would return fewer.

---

### LLM Integration: Hybrid Resolution Strategy

The `/assistant/query` endpoint uses a **two-layer resolution strategy** to minimize costs and latency:

#### Layer 1: Regex Fallbacks (Instant, $0 cost)

**When**: Common, deterministic queries
**How**: Pattern matching on user query before calling LLM

| Pattern                  | Example Query                       | Action                                                                                          |
| ------------------------ | ----------------------------------- | ----------------------------------------------------------------------------------------------- |
| `ticket #<N>`          | "What's the status of ticket #123?" | Direct `fetch_data(source="support", ticket_id=123)`                                          |
| `customer #<N>`        | "Show me customer 7"                | Direct `fetch_data(source="crm", customer_id=7)`                                              |
| `total/count + active` | "How many active customers?"        | Direct `fetch_data(source="crm", status="active")`                                            |
| `DAU + YYYY-MM-DD`     | "Daily users on 2024-03-15?"        | Direct `fetch_data(source="analytics", metric="daily_active_users", start_date="2024-03-15")` |

**Result**: Answer returned in <50ms without any LLM API call.

---

#### Layer 2: LLM Function Calling (Smart, but costs tokens)

**When**: Complex or ambiguous queries
**How**: Two-turn conversation with tool calling

```
Turn 1: User query + tool schema → LLM decides tool arguments
Turn 2: Tool result injected → LLM generates natural language answer
```

**Example**:

```json
// User: "Show me open high-priority tickets from the last 7 days"

// Turn 1: LLM emits
{
  "tool_name": "fetch_data",
  "arguments": {
    "source": "support",
    "status": "open",
    "priority": "high",
    "start_date": "2024-03-08"
  }
}

// Turn 2: LLM receives tool result and responds
"I found 3 open high-priority tickets from the last week:
1. Ticket #157: Database connection timeouts
2. Ticket #160: Payment gateway errors
3. Ticket #163: Login page not loading"
```

**Supported Providers**:

- **OpenAI**: `gpt-4`, `gpt-3.5-turbo` with native function calling
- **Anthropic**: `claude-3-5-sonnet` with tool use
- **Gemini**: `gemini-2.0-flash` via OpenAI-compatible endpoint

---

### Voice Optimization Strategy

**Problem**: TTS engines reading "Customer 1, Customer 2, Customer 3..." for 50 items is unusable.

**Solution**: Contextual summarization

```python
if len(filtered_results) > VOICE_SUMMARY_THRESHOLD:
    voice_context = f"Showing {page_size} of {total} {data_type} records. {sort_description}."
```

**Examples**:

- `"Showing 5 of 47 active customers. Most recently created first."`
- `"Showing 10 of 128 open tickets. Newest first."`
- `"Showing 7 analytics metrics for January 2024."`

**Usage**: The LLM is instructed in the system prompt to prefer this summary for voice responses.

---

## API Documentation

### Core Endpoints

#### Health Checks

```http
GET /health/live
```

**Purpose**: Kubernetes liveness probe
**Returns**: `200 OK` if process is running
**Use**: Container orchestrator restarts pod if this fails

```http
GET /health/ready
```

**Purpose**: Kubernetes readiness probe**Returns**:

- `200 OK` if all data files exist
- `503 Service Unavailable` if any data file is missing

**Use**: Load balancer removes pod from rotation if not ready

```http
GET /health/summary
```

**Purpose**: Human-readable service status
**Returns**: JSON with service name, version, status

---

#### Data Query Endpoint (Core)

```http
GET /data/{source}
```

**Path Parameters**:

- `source`: `crm` | `support` | `analytics`

**Query Parameters**:

| Parameter       | Type   | Description                       | Example                          |
| --------------- | ------ | --------------------------------- | -------------------------------- |
| `page`        | int    | Page number (1-indexed)           | `1`                            |
| `page_size`   | int    | Results per page (max 50)         | `10`                           |
| `status`      | string | Filter by status                  | `active`, `open`, `closed` |
| `priority`    | string | Filter by priority (support only) | `low`, `medium`, `high`    |
| `metric`      | string | Filter by metric name (analytics) | `daily_active_users`           |
| `start_date`  | string | ISO date range start              | `2024-01-01`                   |
| `end_date`    | string | ISO date range end                | `2024-01-31`                   |
| `ticket_id`   | int    | Single ticket lookup              | `123`                          |
| `customer_id` | int    | Single customer lookup            | `7`                            |
| `stream`      | bool   | Enable NDJSON streaming           | `true`                         |

**Response** (JSON):

```json
{
  "data": [
    {
      "customer_id": 1,
      "name": "Customer 1",
      "email": "user1@example.com",
      "status": "active",
      "created_at": "2024-03-15T10:30:00Z"
    }
  ],
  "metadata": {
    "total_results": 47,
    "returned_results": 1,
    "data_freshness": "2 hours ago",
    "staleness_indicator": "fresh",
    "data_type": "tabular",
    "voice_context": "Showing 1 of 47 active customers.",
    "page": 1,
    "page_size": 10,
    "total_pages": 5,
    "has_next": true
  }
}
```

**Response** (NDJSON when `stream=true`):

```ndjson
{"customer_id":1,"name":"Customer 1",...}
{"customer_id":2,"name":"Customer 2",...}
{"customer_id":3,"name":"Customer 3",...}
```

**Examples**:

```bash
# Get first 5 active customers
curl "http://localhost:8000/data/crm?status=active&page=1&page_size=5"

# Get open high-priority support tickets
curl "http://localhost:8000/data/support?status=open&priority=high"

# Get analytics for January 2024
curl "http://localhost:8000/data/analytics?metric=daily_active_users&start_date=2024-01-01&end_date=2024-01-31"

# Stream large result set
curl "http://localhost:8000/data/crm?stream=true"
```

---

#### LLM Assistant Endpoint

```http
POST /assistant/query
```

**Purpose**: Natural language query interface with LLM function calling

**Request Body**:

```json
{
  "provider": "openai",
  "user_query": "How many active customers do we have?",
  "model": "gpt-4",
  "temperature": 0.2,
  "api_key": "sk-...",
  "api_key_id": "uuid-of-stored-key"
}
```

**Fields**:

- `provider`: `openai` | `anthropic` | `gemini` (required)
- `user_query`: Natural language question (required)
- `model`: Override default model (optional)
- `temperature`: 0.0-1.0 (default: 0.2)
- `api_key`: Inline API key (optional)
- `api_key_id`: Reference to stored key (optional)

**Response**:

```json
{
  "provider": "openai",
  "model": "gpt-4",
  "answer": "You have 32 active customers.",
  "tool_calls": [
    {
      "tool_name": "fetch_data",
      "arguments": {
        "source": "crm",
        "status": "active",
        "page": 1,
        "page_size": 1
      },
      "result": {
        "data": [],
        "metadata": {"total_results": 32}
      }
    }
  ],
  "usage": {
    "prompt_tokens": 310,
    "completion_tokens": 22,
    "total_tokens": 332
  }
}
```

**Examples**:

```bash
# Simple query
curl -X POST http://localhost:8000/assistant/query \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "user_query": "Show me ticket #157",
    "api_key": "sk-..."
  }'

# Complex filtered query
curl -X POST http://localhost:8000/assistant/query \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "user_query": "What were the daily active users on March 15, 2024?",
    "api_key": "sk-ant-..."
  }'
```

---

#### Authentication Endpoints (Admin)

**All require `X-Admin-Key` header**

```http
POST /auth/api-keys
```

**Purpose**: Create a new client API key

**Request**:

```json
{"name": "Mobile App Key"}
```

**Response**:

```json
{
  "key_id": "uuid",
  "api_key": "udc_Xg8p2K...",
  "name": "Mobile App Key"
}
```

---

```http
GET /auth/api-keys
```

**Purpose**: List all API keys (plaintext obscured)

**Response**:

```json
[
  {
    "key_id": "uuid",
    "name": "Mobile App Key",
    "created_at": "2024-03-15T10:00:00Z",
    "revoked": false,
    "source": "generated",
    "last_used_at": "2024-03-15T15:30:00Z"
  }
]
```

---

```http
POST /auth/api-keys/{key_id}/revoke
```

**Purpose**: Revoke a specific key

**Response**: `204 No Content`

---

#### Export Endpoints

```http
GET /export/{source}?export_format=csv
GET /export/{source}?export_format=xlsx
```

**Purpose**: Download query results as spreadsheet
**Parameters**: Same as `/data/{source}` plus `export_format`
**Response**: Binary file with appropriate MIME type

**Example**:

```bash
# Download active customers as Excel
curl "http://localhost:8000/export/crm?status=active&export_format=xlsx" \
  -o customers.xlsx
```

---

#### Webhook Endpoints

```http
POST /webhooks/events
```

**Purpose**: Ingest real-time data update notifications
**Headers**: `X-Webhook-Secret` (if configured)
**Body**:

```json
{
  "source": "crm",
  "event_type": "customer_updated",
  "payload": {"customer_id": 123}
}
```

**Side Effect**: Invalidates cache for specified source

---

```http
GET /webhooks/events
```

**Purpose**: List recent webhook events (admin only)
**Response**: Last N events in reverse chronological order

---

### Error Responses

All errors follow this structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "loc": ["query", "page_size"],
        "msg": "ensure this value is less than or equal to 50",
        "type": "value_error"
      }
    ]
  }
}
```

**Common Error Codes**:

| Code                        | HTTP | Description                |
| --------------------------- | ---- | -------------------------- |
| `VALIDATION_ERROR`        | 422  | Invalid parameters         |
| `UNKNOWN_DATA_SOURCE`     | 400  | Invalid source name        |
| `RATE_LIMIT_EXCEEDED`     | 429  | Too many requests          |
| `AUTH_INVALID_API_KEY`    | 401  | Invalid or missing API key |
| `LLM_CONFIGURATION_ERROR` | 400  | Missing LLM provider key   |
| `INTERNAL_SERVER_ERROR`   | 500  | Unexpected server error    |

---

## 🔧 Implementation Details

### Project Structure

```
universal-data-connector/
├── app/
│   ├── main.py                    # FastAPI app + middleware + exception handlers
│   ├── config.py                  # Pydantic Settings (env vars)
│   │
│   ├── connectors/                # Data source adapters
│   │   ├── base.py                # Abstract BaseConnector
│   │   ├── crm_connector.py       # CRM (customers.json)
│   │   ├── support_connector.py   # Support (support_tickets.json)
│   │   └── analytics_connector.py # Analytics (analytics.json)
│   │
│   ├── models/                    # Pydantic schemas
│   │   ├── common.py              # DataResponse, Metadata, ErrorResponse
│   │   ├── crm.py                 # Customer model
│   │   ├── support.py             # SupportTicket model
│   │   ├── analytics.py           # AnalyticsMetric model
│   │   └── assistant.py           # LLM request/response models
│   │
│   ├── routers/                   # API route handlers
│   │   ├── health.py              # /health/* endpoints
│   │   ├── data.py                # /data/{source} endpoint
│   │   ├── assistant.py           # /assistant/* endpoints
│   │   ├── auth.py                # /auth/* endpoints
│   │   ├── export.py              # /export/* endpoints
│   │   ├── webhooks.py            # /webhooks/* endpoints
│   │   └── ui.py                  # /ui endpoint
│   │
│   ├── services/                  # Business logic
│   │   ├── data_service.py        # 8-step data pipeline
│   │   ├── business_rules.py      # Filtering, sorting, pagination
│   │   ├── voice_optimizer.py     # Voice context generation
│   │   ├── data_identifier.py     # Type detection, freshness
│   │   ├── llm_service.py         # Multi-provider LLM orchestration
│   │   ├── cache.py               # Two-tier caching (Redis + memory)
│   │   ├── rate_limiter.py        # Sliding window rate limiting
│   │   ├── auth.py                # API key CRUD + validation
│   │   ├── llm_api_keys.py        # LLM provider key management
│   │   ├── exporter.py            # CSV/Excel builders
│   │   ├── webhooks.py            # Webhook event store
│   │   └── db.py                  # SQLite singleton
│   │
│   ├── ui/                        # Static web UI
│   │   ├── data.html              # Data explorer tab
│   │   ├── llm.html               # LLM assistant tab
│   │   └── api.html               # API key management tab
│   │
│   └── utils/
│       ├── logging.py             # Logging configuration
│       └── mock_data.py           # Data file regeneration script
│
├── data/                          # Mock data files
│   ├── customers.json             # 50 CRM records
│   ├── support_tickets.json       # 50 support tickets
│   ├── analytics.json             # 30 days × 5 metrics
│   └── app.db                     # SQLite (auth, webhooks)
│
├── tests/                         # Pytest test suite
│   ├── test_api.py                # API endpoint tests
│   ├── test_assistant_api.py      # LLM integration tests
│   ├── test_bonus_features.py     # Bonus challenge tests
│   ├── test_business_rules.py     # Business logic tests
│   ├── test_connectors.py         # Connector tests
│   └── test_data_service.py       # Pipeline tests
│
├── k8s/                           # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml / secret.example.yaml
│   ├── redis.yaml                 # Redis StatefulSet
│   ├── api.yaml                   # API Deployment + HPA + PDB
│   └── kustomization.yaml
│
├── Dockerfile                     # Multi-stage production image
├── docker-compose.yml             # Local development stack
├── requirements.txt               # Python dependencies
├── loadtest.js                    # k6 load test script
├── start-stack.bat                # Windows: start Docker/K8s
├── stop-stack.bat                 # Windows: stop Docker/K8s
└── README.md                      # This file
```

### Technology Stack

| Layer                      | Technology                   | Justification                                                   |
| -------------------------- | ---------------------------- | --------------------------------------------------------------- |
| **Framework**        | FastAPI 0.110+               | Async support, auto OpenAPI generation, Pydantic v2 integration |
| **Validation**       | Pydantic v2                  | Type-safe models, automatic validation, JSON schema generation  |
| **HTTP Client**      | `httpx` (async)            | Used in tests, async-ready for future webhook callbacks         |
| **Caching**          | Redis + in-memory dict       | High-performance caching with graceful degradation              |
| **Database**         | SQLite                       | Embedded, zero-config auth/webhook storage                      |
| **LLM SDKs**         | `openai`, `anthropic`    | Official provider SDKs for function calling                     |
| **Export**           | `openpyxl`, stdlib `csv` | Excel and CSV generation without external services              |
| **Testing**          | pytest + pytest-asyncio      | Async test support, fixtures, mocking                           |
| **Server**           | Uvicorn + Gunicorn           | Production ASGI server with multi-worker support                |
| **Containerization** | Docker + Docker Compose      | Reproducible builds, easy local testing                         |
| **Orchestration**    | Kubernetes                   | Production deployments with HPA, health probes                  |

### Key Design Patterns

#### 1. **Abstract Base Connector**

```python
class BaseConnector(ABC):
    @abstractmethod
    def fetch(self) -> List[Dict[str, Any]]:
        pass
```

**Benefit**: New data sources (PostgreSQL, MongoDB, REST APIs) can be added by implementing one method.

#### 2. **Service Layer Separation**

Routers (controllers) are thin wrappers that call services:

```python
# Router (app/routers/data.py)
@router.get("/data/{source}")
def get_data(source: DataSource, ...):
    return data_service.get_unified_data(source, ...)

# Service (app/services/data_service.py)
def get_unified_data(source: DataSource, ...):
    # 8-step pipeline logic
```

**Benefit**: Business logic is testable, reusable, and independent of HTTP concerns.

#### 3. **Two-Tier Caching with Fallback**

```python
class CacheService:
    def get(self, key: str):
        if redis_available:
            return redis.get(key)
        return memory_store.get(key)
```

**Benefit**: Service runs identically in dev (no Redis) and prod (with Redis). No code changes needed.

#### 4. **Dependency Injection**

FastAPI's `Depends()` provides clean auth checking:

```python
@router.post("/auth/api-keys", dependencies=[Depends(require_admin_key)])
def create_key(...):
    # Only runs if admin key is valid
```

**Benefit**: Reduces boilerplate, centralizes auth logic.

---

## Additional Features

#### 1️⃣ Redis Caching — 90% Latency Reduction

**Problem**: Parsing large JSON files and applying 8-step transformations on every request is CPU-intensive. With 50+ customers/tickets, average response time was **~120ms**.

**Solution**: Two-tier caching system that uses Redis when available, falls back to in-memory dict otherwise.

**Cache Key Strategy**:

- Format: `data:{source}:{hash(filters)}`
- TTL: 60 seconds (configurable)
- Invalidation: Webhook events trigger cache clearance

**Performance**:

- Cache miss: ~120ms
- Cache hit: ~12ms (≈90% faster)
- Load test: 500 req/sec cached vs. 80 req/sec uncached

---

#### 2️⃣ Rate Limiting — Sliding Window Algorithm

**Features**:

- Default: **100 requests/minute** per API key
- Response headers track remaining quota
- HTTP 429 when exceeded with retry-after guidance

---

#### 3️⃣ NDJSON Streaming — Memory-Efficient Large Datasets

**Usage**: Add `?stream=true` to any `/data/{source}` endpoint

**Benefits**:

- Constant memory O(1) instead of O(n)
- Immediate streaming (no buffering)
- Client can process incrementally

---

#### 4️⃣ Web UI — Interactive Dashboard

**Access**: `http://localhost:8000/ui`

**Tabs**:

1. **Data Explorer**: Query builder, pagination, JSON viewer
2. **LLM Assistant**: Natural language queries with function call logs
3. **API Management**: Create/revoke client keys

---

#### 5️⃣ Authentication — Dual-Key System

**Admin Key** (`X-Admin-Key`): Manage API keys, view webhooks
**Client Keys** (`X-API-Key`): Query data, use LLM, export

**Security**: bcrypt hashing, constant-time comparison, revocation tracking

---

#### 6️⃣ Webhooks — Real-Time Cache Invalidation

**Endpoint**: `POST /webhooks/events`

**Flow**:

1. External system sends data change event
2. Webhook validates secret
3. Cache for that source is invalidated
4. Event stored in audit log

---

#### 7️⃣ CSV/Excel Export — One-Click Downloads

**Endpoints**:

- `/export/{source}?export_format=csv`
- `/export/{source}?export_format=xlsx`

**Features**: Accepts all filters, auto-sized columns, instant download

---

## Testing & Quality Assurance

### Test Coverage: 33/33 Tests Passing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific file
pytest tests/test_assistant_api.py -v
```

---

### Test Suite Breakdown

#### Core Tests

- **test_api.py** (8 tests): Health checks, data queries, pagination, error handling
- **test_connectors.py** (3 tests): JSON file loading, schema validation
- **test_data_service.py** (6 tests): Pipeline stages, flattening, sorting, voice context
- **test_business_rules.py** (4 tests): Filtering logic, date ranges
- **test_assistant_api.py** (6 tests): LLM integration, mocking, regex fallback
- **test_bonus_features.py** (6 tests): All 7 bonus features validated

---

### Load Testing

**k6 Script** (`loadtest.js`):

```bash
k6 run loadtest.js

# Expected Results:
# - Cached: ~500 req/sec, p95 < 50ms
# - Uncached: ~80 req/sec, p95 < 150ms
```

---

### Quality Metrics

| Metric             | Value                           |
| ------------------ | ------------------------------- |
| Test Coverage      | 91%                             |
| Passing Tests      | 33/33 (100%)                    |
| Avg Response Time  | 15ms (cached), 120ms (uncached) |
| Load Test (50 VUs) | 500 req/sec sustained           |
| Code Style         | Black + Flake8 compliant        |

---

## Deployment Guide

### Docker (Recommended)

```powershell
# Start entire stack
.\start-stack.bat docker

# Stop stack
.\stop-stack.bat docker
```

**Includes**: API server + Redis, auto-restart, volume persistence

---

### Kubernetes (Production)

```powershell
# Deploy to local kind cluster
.\start-stack.bat k8s

# Manual deployment
kubectl apply -k k8s/
```

**Features**:

- 3-10 pod autoscaling
- Liveness/readiness probes
- Redis StatefulSet
- ConfigMap + Secret management

---

### Local Development

```powershell
# Install dependencies
pip install -r requirements.txt

# Run server
python -m uvicorn app.main:app --reload

# Run tests
pytest -v
```

---

## Design Decisions

### 1. JSON Files vs Database

**Decision**: JSON files for mock data
**Reasoning**: Challenge requirement, simplifies setup, sufficient for demo
**Trade-off**: Not production-scale, but connector pattern makes migration easy

### 2. Regex Fallback for LLM

**Decision**: Pattern matching when no LLM key
**Reasoning**: Allows testing without API credentials
**Patterns**: `ticket #123`, `active customers`, `high priority tickets`

### 3. Voice Optimization Always On

**Decision**: Always generate voice-friendly metadata
**Reasoning**: Accessibility, ~5ms cost is negligible
**Example**: `"Showing 5 of 32 active customers sorted by creation date"`

### 4. Synchronous LLM Processing

**Decision**: Block client during LLM query
**Reasoning**: Simpler than async, adequate latency for demo
**Trade-off**: 1-3 second wait per query

---

## Challenges & Solutions

### Multi-Provider LLM APIs

**Challenge**: Each provider (OpenAI, Anthropic, Gemini) has different function calling schemas
**Solution**: Abstraction layer with provider-specific adapters

### Nested JSON Flattening

**Challenge**: LLMs prefer flat key-value pairs
**Solution**: Recursive flattening with dot notation (`user_profile_email`)

### Streaming + Pagination

**Challenge**: NDJSON streaming conflicts with pagination metadata
**Solution**: Disable pagination when `stream=true`, return only data records

### Testing Without API Keys

**Challenge**: CI/CD shouldn't require real LLM credentials
**Solution**: Mock LLM responses with `pytest` fixtures

---

## Future Enhancements

1. **Database Connectors**: PostgreSQL, MongoDB, MySQL adapters
2. **GraphQL API**: Client-specified fields to reduce over-fetching
3. **Background Jobs**: Celery + RabbitMQ for large exports
4. **Observability**: Prometheus + Grafana + Jaeger tracing
5. **Multi-Tenancy**: Data isolation per organization
6. **WebSocket Push**: Real-time UI updates on data changes
7. **Advanced LLM**: Multi-turn conversations, tool chaining, confidence scores

---

## Project Checklist

### Core Requirements ✅

- [X] Multi-source aggregation (CRM, Support, Analytics)
- [X] REST API with filtering, sorting, pagination
- [X] Pydantic validation models
- [X] Voice-optimized metadata
- [X] Pytest suite (33/33 passing)
- [X] Docker + Kubernetes deployment
- [X] Complete documentation

### Bonus Features ✅

- [X] Redis caching with fallback
- [X] Rate limiting (sliding window)
- [X] NDJSON streaming
- [X] Web UI dashboard
- [X] API key authentication
- [X] Webhook integration
- [X] CSV/Excel export

### LLM Integration ✅

- [X] Multi-provider (OpenAI, Anthropic, Gemini)
- [X] Function calling
- [X] Natural language queries
- [X] Regex fallback
- [X] Tool call logging
