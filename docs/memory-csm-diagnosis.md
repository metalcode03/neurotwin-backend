# Memory & CSM Architecture Diagnosis

## Executive Summary

The frontend expects memory-specific endpoints (`/api/v1/csm/memories`) but the backend only has CSM profile endpoints. There's architectural confusion between:
- **CSM (Cognitive Signature Model)**: Personality profile, traits, tone preferences
- **Memory**: Learning events, interactions, embeddings for semantic search

## Current State Analysis

### Frontend Expectations (from `useMemory.ts` and `api.ts`)

1. **Memory List Endpoint**: `GET /api/v1/csm/memories?q={query}`
   - Returns: `MemoryEntry[]`
   - Features: Search functionality, pagination
   
2. **Memory Detail Endpoint**: `GET /api/v1/csm/memories/{memoryId}`
   - Returns: Single `MemoryEntry` with full details
   
3. **Personality Profile Endpoint**: `GET /api/v1/csm/profile`
   - Returns: `PersonalityProfile` (CSM-derived data)

### Backend Reality

**CSM App** (`apps/csm/`):
- ✅ Has: Profile management, versioning, rollback
- ✅ Endpoints: `/profile`, `/history`, `/history/{version}`, `/rollback`
- ❌ Missing: Memory list, memory detail, personality profile transformation

**Memory App** (`apps/memory/`):
- ✅ Has: Vector memory engine, embedding storage, semantic search
- ✅ Models: `MemoryRecord`, `MemoryAccessLog`
- ✅ Services: `VectorMemoryEngine` with async operations
- ❌ Missing: REST API views, URL configuration, serializers

### URL Path Mismatch

**Frontend expects**: `/api/v1/csm/memories/*`
**Backend has**: No memory endpoints at all

**Options**:
1. Add memory endpoints under CSM (`/api/v1/csm/memories/*`) ✅ RECOMMENDED
2. Create separate memory namespace (`/api/v1/memory/*`)
3. Merge into CSM profile endpoint

**Recommendation**: Option 1 - Memory is part of the cognitive model, so nesting under CSM makes semantic sense.

## What is Memory Used For?

### Purpose
Memory stores **learning events** - interactions that shape the Twin's understanding:
- Conversations with the user
- Actions taken by the Twin
- User feedback on Twin behavior
- System-generated learning insights

### Architecture
```
┌─────────────────────────────────────────────────────┐
│                   CSM Profile                        │
│  (Personality, Tone, Habits, Decision Style)        │
│              Stored in PostgreSQL                    │
└─────────────────────────────────────────────────────┘
                        ↑
                        │ Influences
                        │
┌─────────────────────────────────────────────────────┐
│                 Memory Records                       │
│  (Learning Events with Embeddings)                   │
│   - PostgreSQL: Metadata, timestamps, source        │
│   - Vector DB: Embeddings for semantic search       │
└─────────────────────────────────────────────────────┘
```

### Relationship
- **CSM**: Static personality snapshot (versioned)
- **Memory**: Dynamic learning history (append-only)
- **Flow**: Memories → Learning Service → CSM Updates

## Missing Backend Features

### 1. Memory REST API (`apps/memory/views.py`)
```python
# Needed views:
- MemoryListView: GET /api/v1/csm/memories
- MemoryDetailView: GET /api/v1/csm/memories/{id}
- MemorySearchView: POST /api/v1/csm/memories/search
```

### 2. Memory Serializers (`apps/memory/serializers.py`)
```python
# Needed serializers:
- MemoryEntrySerializer: Transform MemoryRecord → Frontend format
- MemorySearchSerializer: Validate search queries
```

### 3. Memory URL Configuration (`apps/memory/urls.py`)
```python
# Needed routes:
- memories/
- memories/<uuid:memory_id>
- memories/search
```

### 4. CSM Profile Transformation
The frontend expects a simplified `PersonalityProfile` format:
```typescript
{
  userId: string;
  traits: string[];           // Extracted from personality
  tonePreferences: string[];  // Extracted from tone
  communicationStyle: string; // Formatted from communication
  decisionPatterns: string[]; // Extracted from decision_style
  updatedAt: string;
}
```

Current CSM returns raw JSONB structure. Need transformation layer.

### 5. Integration in Core API URLs
Add memory routes to CSM namespace in `core/api/urls.py`.

## Frontend Type Definitions

### Current Types (`neuro-frontend/src/types/memory.ts`)
```typescript
interface PersonalityProfile {
  userId: string;
  traits: string[];
  tonePreferences: string[];
  communicationStyle: string;
  decisionPatterns: string[];
  updatedAt: string;
}

interface MemoryEntry {
  id: string;
  eventType: string;
  timestamp: string;
  description: string;
  source: string;
  metadata?: Record<string, unknown>;
}
```

### Backend Mapping
- `MemoryEntry.eventType` → Derived from `MemoryRecord.source`
- `MemoryEntry.description` → `MemoryRecord.content`
- `MemoryEntry.source` → `MemoryRecord.source`
- `MemoryEntry.metadata` → `MemoryRecord.metadata`

## Implementation Plan

### Phase 1: Memory API (Priority: HIGH)
1. Create `apps/memory/serializers.py`
2. Create `apps/memory/views.py`
3. Create `apps/memory/urls.py`
4. Update `apps/csm/urls.py` to include memory routes

### Phase 2: CSM Profile Transformation (Priority: HIGH)
1. Add `get_personality_profile()` method to `CSMService`
2. Create `PersonalityProfileSerializer`
3. Add `/api/v1/csm/profile` endpoint (already exists, needs enhancement)

### Phase 3: Integration (Priority: MEDIUM)
1. Update `core/api/urls.py` to include memory namespace
2. Add memory endpoints to API documentation
3. Update frontend API client if needed

### Phase 4: Testing (Priority: MEDIUM)
1. Unit tests for memory serializers
2. Integration tests for memory endpoints
3. E2E tests for memory search functionality

## Security Considerations

1. **Authentication**: All memory endpoints require `IsAuthenticated`
2. **Authorization**: Users can only access their own memories
3. **Rate Limiting**: Memory search should be rate-limited
4. **Data Privacy**: Memory content may contain sensitive information
5. **Audit Logging**: All memory access should be logged (already implemented in `MemoryAccessLog`)

## Performance Considerations

1. **Pagination**: Memory list should support cursor-based pagination
2. **Caching**: Personality profile can be cached (changes infrequently)
3. **Async Operations**: Memory search uses async vector DB operations
4. **Indexing**: Ensure proper database indexes on `user_id`, `created_at`, `source`

## Recommendations

### Immediate Actions
1. ✅ Implement memory REST API endpoints
2. ✅ Add personality profile transformation
3. ✅ Update URL routing to match frontend expectations
4. ✅ Add proper serializers with validation

### Future Enhancements
1. Add memory deletion endpoint (GDPR compliance)
2. Add memory export functionality
3. Implement memory analytics (most accessed, relevance trends)
4. Add memory tagging/categorization
5. Implement memory consolidation (merge similar memories)

### Documentation Needs
1. API documentation for memory endpoints
2. Memory architecture diagram
3. CSM vs Memory distinction guide
4. Frontend integration examples
