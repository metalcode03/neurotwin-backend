# Memory & CSM Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     NeuroTwin Frontend                           │
│                    (Next.js Dashboard)                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTP/REST API
                         │ JWT Authentication
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Django REST Framework                         │
│                   /api/v1/csm/* endpoints                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌──────────────────┐           ┌──────────────────┐
│   CSM Module     │           │  Memory Module   │
│  (Personality)   │           │  (Learning)      │
└────────┬─────────┘           └────────┬─────────┘
         │                               │
         │                               │
         ▼                               ▼
┌──────────────────┐           ┌──────────────────┐
│   PostgreSQL     │           │   PostgreSQL     │
│  csm_profiles    │           │ memory_records   │
│  (JSONB data)    │           │  (metadata)      │
└──────────────────┘           └────────┬─────────┘
                                        │
                                        │
                                        ▼
                               ┌──────────────────┐
                               │   Vector DB      │
                               │  (embeddings)    │
                               └──────────────────┘
```

## Data Flow: Memory Creation

```
1. User Interaction
   │
   ▼
2. Frontend captures event
   │
   ▼
3. POST /api/v1/csm/memories
   │
   ▼
4. MemoryCreateView validates
   │
   ▼
5. VectorMemoryEngine.store_memory()
   │
   ├─► Generate embedding (async)
   │   │
   │   ▼
   │   EmbeddingGenerator
   │   (Google GenAI)
   │
   ├─► Store metadata
   │   │
   │   ▼
   │   PostgreSQL
   │   (MemoryRecord)
   │
   └─► Store embedding
       │
       ▼
       Vector DB
       (semantic search)
```

## Data Flow: Personality Profile

```
1. Frontend requests profile
   │
   ▼
2. GET /api/v1/csm/profile
   │
   ▼
3. CSMPersonalityProfileView
   │
   ▼
4. CSMService.get_profile()
   │
   ▼
5. Load from PostgreSQL
   │
   ▼
6. Transform JSONB → PersonalityProfile
   │
   ├─► Extract traits
   ├─► Extract tone preferences
   ├─► Format communication style
   └─► Extract decision patterns
   │
   ▼
7. Return simplified format
   │
   ▼
8. Frontend displays
```

## Data Flow: Memory Search

```
1. User enters search query
   │
   ▼
2. POST /api/v1/csm/memories/search
   │
   ▼
3. MemorySearchView validates
   │
   ▼
4. VectorMemoryEngine.retrieve_relevant()
   │
   ├─► Generate query embedding
   │   │
   │   ▼
   │   EmbeddingGenerator
   │
   ├─► Search vector DB
   │   │
   │   ▼
   │   Vector DB
   │   (cosine similarity)
   │
   ├─► Get metadata from PostgreSQL
   │   │
   │   ▼
   │   MemoryRecord.objects.get()
   │
   ├─► Calculate combined score
   │   (relevance + recency)
   │
   └─► Log access
       │
       ▼
       MemoryAccessLog
```

## Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Memory Page  │  │ useMemory    │  │ API Client   │     │
│  │ (UI)         │─►│ (Hook)       │─►│ (HTTP)       │     │
│  └──────────────┘  └──────────────┘  └──────┬───────┘     │
└────────────────────────────────────────────────┼────────────┘
                                                 │
                                                 │ REST API
                                                 │
┌────────────────────────────────────────────────┼────────────┐
│                        Backend                 │             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────▼───────┐   │
│  │ CSM Views    │  │ Memory Views │  │ Serializers    │   │
│  │              │  │              │  │                │   │
│  └──────┬───────┘  └──────┬───────┘  └────────────────┘   │
│         │                 │                                 │
│         ▼                 ▼                                 │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │ CSM Service  │  │ Memory       │                       │
│  │              │  │ Service      │                       │
│  └──────┬───────┘  └──────┬───────┘                       │
│         │                 │                                 │
│         ▼                 ▼                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ CSM Models   │  │ Memory       │  │ Vector       │   │
│  │              │  │ Models       │  │ Client       │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## URL Routing Structure

```
/api/v1/
├── auth/
│   ├── login
│   ├── register
│   └── refresh
│
├── csm/
│   ├── profile              ← Personality profile (frontend format)
│   ├── profile/raw          ← Raw CSM data (JSONB)
│   ├── history              ← Version history
│   ├── history/{version}    ← Specific version
│   ├── rollback             ← Rollback to version
│   │
│   └── memories/            ← Memory endpoints (nested)
│       ├── GET/POST         ← List/Create memories
│       ├── {id}             ← Memory detail
│       ├── search           ← Semantic search
│       └── stats            ← Statistics
│
├── twin/
├── subscription/
├── voice/
└── ...
```

## Database Schema

### CSM Tables

```sql
-- CSM Profile (Personality)
csm_profiles
├── id (UUID, PK)
├── user_id (UUID, FK)
├── version (INT)
├── profile_data (JSONB)  ← Personality, tone, habits, decisions
├── is_current (BOOL)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

-- CSM Change Log (Audit)
csm_change_logs
├── id (UUID, PK)
├── profile_id (UUID, FK)
├── from_version (INT)
├── to_version (INT)
├── change_type (VARCHAR)
├── change_summary (JSONB)
└── changed_at (TIMESTAMP)
```

### Memory Tables

```sql
-- Memory Records (Metadata)
memory_records
├── id (UUID, PK)
├── user_id (UUID, FK)
├── content (TEXT)
├── content_hash (VARCHAR)
├── source (VARCHAR)        ← conversation, action, feedback, etc.
├── metadata (JSONB)
├── vector_id (VARCHAR)     ← Reference to vector DB
├── has_embedding (BOOL)
├── embedding_model (VARCHAR)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

-- Memory Access Log (Audit)
memory_access_logs
├── id (UUID, PK)
├── memory_id (UUID, FK)
├── accessed_at (TIMESTAMP)
├── access_type (VARCHAR)   ← retrieval, validation, export
└── context (JSONB)
```

### Vector Database

```
Vector Store (External)
├── id (UUID)               ← Matches memory_records.id
├── embedding (VECTOR)      ← 768-dimensional vector
└── metadata (JSON)         ← user_id, source, timestamp
```

## Security Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Request Flow                          │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 1: JWT Authentication                            │
│  ✓ Valid token required                                 │
│  ✓ Token not expired                                    │
│  ✓ User exists and active                               │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2: User Verification                             │
│  ✓ Email verified                                       │
│  ✓ Account not suspended                                │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Resource Authorization                        │
│  ✓ User owns the resource                               │
│  ✓ Query filtered by user_id                            │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Audit Logging                                 │
│  ✓ Access logged to MemoryAccessLog                     │
│  ✓ Timestamp, type, context recorded                    │
└─────────────────────────────────────────────────────────┘
```

## Memory Lifecycle

```
┌─────────────┐
│   Created   │  ← User interaction captured
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Embedding  │  ← Async embedding generation
│  Generated  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Stored    │  ← Saved to PostgreSQL + Vector DB
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Searchable  │  ← Available for semantic search
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Retrieved  │  ← Used in Twin responses
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Logged    │  ← Access logged for audit
└─────────────┘
```

## CSM Update Flow

```
┌─────────────┐
│  Memories   │  ← Learning events accumulate
│ Accumulate  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Learning   │  ← Analysis of patterns
│  Service    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Update    │  ← CSM profile updated
│  Triggered  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ New Version │  ← New version created
│   Created   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Change    │  ← Change logged
│   Logged    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Previous   │  ← Old version archived
│  Archived   │
└─────────────┘
```

## Performance Optimization

```
┌─────────────────────────────────────────────────────────┐
│                   Optimization Layers                    │
└─────────────────────────────────────────────────────────┘

1. Database Level
   ├─► Indexes on user_id, created_at, source
   ├─► Query optimization with filters
   └─► Connection pooling

2. Application Level
   ├─► Async operations for vector DB
   ├─► Pagination to limit results
   └─► Query result caching (TODO)

3. API Level
   ├─► Rate limiting (TODO)
   ├─► Response compression
   └─► CDN for static assets

4. Vector DB Level
   ├─► Approximate nearest neighbor (ANN)
   ├─► Index optimization
   └─► Batch operations
```

## Error Handling Flow

```
Request
  │
  ▼
Try
  │
  ├─► Success ──────────────────────► 200/201 Response
  │
  └─► Error
      │
      ├─► Authentication Error ─────► 401 Unauthorized
      │
      ├─► Authorization Error ───────► 403 Forbidden
      │
      ├─► Validation Error ──────────► 400 Bad Request
      │
      ├─► Not Found Error ───────────► 404 Not Found
      │
      └─► Server Error ──────────────► 500 Internal Error
          │
          └─► Log to Django logs
              └─► Return generic error message
```

---

This architecture ensures:
- ✅ Clear separation of concerns
- ✅ Scalable data storage
- ✅ Secure access control
- ✅ Comprehensive audit trails
- ✅ Performance optimization
- ✅ Error resilience
