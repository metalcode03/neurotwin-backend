# Memory API Reference for Frontend

Quick reference for integrating memory features in the NeuroTwin dashboard.

## Base URL
```
/api/v1/csm
```

## Authentication
All endpoints require JWT authentication via `Authorization: Bearer <token>` header.

---

## Personality Profile

### Get Personality Profile
```http
GET /api/v1/csm/profile
```

**Response:**
```json
{
  "success": true,
  "message": "Success",
  "data": {
    "userId": "uuid",
    "traits": [
      "Creative & Open-minded",
      "Organized & Disciplined",
      "Outgoing & Energetic"
    ],
    "tonePreferences": [
      "Formal & Professional",
      "Warm & Friendly",
      "Direct & Clear"
    ],
    "communicationStyle": "Moderate responses with minimal emoji usage",
    "decisionPatterns": [
      "Comfortable with calculated risks",
      "Values thoroughness and accuracy",
      "Prefers collaborative decision-making"
    ],
    "updatedAt": "2024-01-26T10:30:00Z"
  }
}
```

**Error Cases:**
- `404`: No CSM profile found (user needs to complete onboarding)
- `401`: Unauthorized

---

## Memory List

### List Memories
```http
GET /api/v1/csm/memories?q={query}&source={source}&limit={limit}&offset={offset}
```

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | No | - | Search query text |
| `source` | string | No | - | Filter by source: `conversation`, `action`, `feedback`, `learning`, `system` |
| `limit` | integer | No | 20 | Max results (1-100) |
| `offset` | integer | No | 0 | Pagination offset |

**Response:**
```json
{
  "success": true,
  "message": "Success",
  "data": {
    "memories": [
      {
        "id": "uuid",
        "eventType": "Conversation",
        "timestamp": "2024-01-26T10:30:00Z",
        "description": "User discussed project deadlines and priorities",
        "source": "conversation",
        "metadata": {
          "duration": "5 minutes",
          "topics": ["work", "planning"]
        }
      }
    ],
    "total": 42,
    "hasMore": true,
    "nextCursor": 20
  }
}
```

**Example Usage:**
```typescript
// List all memories
const response = await api.memory.list();

// Search memories
const response = await api.memory.list('project deadlines');

// Filter by source
const response = await api.memory.list('', { source: 'conversation' });
```

---

## Memory Detail

### Get Memory Detail
```http
GET /api/v1/csm/memories/{memoryId}
```

**Response:**
```json
{
  "success": true,
  "message": "Success",
  "data": {
    "id": "uuid",
    "eventType": "Conversation",
    "timestamp": "2024-01-26T10:30:00Z",
    "description": "User discussed project deadlines and priorities",
    "source": "conversation",
    "metadata": {
      "duration": "5 minutes",
      "topics": ["work", "planning"]
    },
    "contentHash": "sha256-hash",
    "hasEmbedding": true,
    "embeddingModel": "MockEmbeddingGenerator",
    "vectorId": "uuid",
    "updatedAt": "2024-01-26T10:30:00Z"
  }
}
```

**Error Cases:**
- `404`: Memory not found or doesn't belong to user
- `401`: Unauthorized

---

## Semantic Search

### Search Memories (Vector-based)
```http
POST /api/v1/csm/memories/search
```

**Request Body:**
```json
{
  "query": "project deadlines",
  "max_results": 10,
  "min_relevance": 0.5,
  "recency_weight": 0.3,
  "source_filter": ["conversation", "action"]
}
```

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query text |
| `max_results` | integer | No | 10 | Max results to return |
| `min_relevance` | float | No | 0.5 | Minimum similarity score (0-1) |
| `recency_weight` | float | No | 0.3 | Weight for recency vs relevance (0-1) |
| `source_filter` | array | No | - | Filter by source types |

**Response:**
```json
{
  "success": true,
  "message": "Success",
  "data": {
    "memories": [...],
    "total": 5,
    "query": "project deadlines"
  }
}
```

**Note:** This uses vector embeddings for semantic similarity, not just keyword matching.

---

## Create Memory

### Create New Memory
```http
POST /api/v1/csm/memories
```

**Request Body:**
```json
{
  "content": "User prefers morning meetings and dislikes last-minute changes",
  "source": "feedback",
  "metadata": {
    "category": "preferences",
    "importance": "high"
  }
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | Memory content (max 10,000 chars) |
| `source` | string | No | Source type (default: `conversation`) |
| `metadata` | object | No | Additional metadata |

**Response:**
```json
{
  "success": true,
  "message": "Success",
  "data": {
    "id": "uuid",
    "eventType": "User Feedback",
    "timestamp": "2024-01-26T10:30:00Z",
    "description": "User prefers morning meetings and dislikes last-minute changes",
    "source": "feedback",
    "metadata": {
      "category": "preferences",
      "importance": "high"
    },
    "hasEmbedding": true,
    "embeddingModel": "MockEmbeddingGenerator"
  }
}
```

**Status Codes:**
- `201`: Created successfully
- `400`: Validation error
- `401`: Unauthorized
- `500`: Server error (embedding generation failed)

---

## Memory Statistics

### Get Memory Stats
```http
GET /api/v1/csm/memories/stats
```

**Response:**
```json
{
  "success": true,
  "message": "Success",
  "data": {
    "total_memories": 42,
    "by_source": {
      "conversation": 25,
      "action": 10,
      "feedback": 5,
      "learning": 2
    },
    "recent_count": 8
  }
}
```

**Fields:**
- `total_memories`: Total number of memories for user
- `by_source`: Breakdown by source type
- `recent_count`: Memories created in last 7 days

---

## Memory Sources

| Source | Event Type | Description |
|--------|-----------|-------------|
| `conversation` | Conversation | Chat interactions with user |
| `action` | Action Taken | Actions performed by Twin |
| `feedback` | User Feedback | Explicit user feedback |
| `learning` | Learning Insight | System-generated insights |
| `system` | System Event | System-level events |

---

## Error Handling

All endpoints follow the standard error response format:

```json
{
  "success": false,
  "message": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

**Common Error Codes:**
- `PROFILE_NOT_FOUND`: CSM profile doesn't exist
- `MEMORY_NOT_FOUND`: Memory doesn't exist or unauthorized
- `VALIDATION_ERROR`: Invalid request data
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Insufficient permissions

---

## Frontend Integration Examples

### Using with React Query

```typescript
// In useMemory.ts
export function useMemory() {
  const memoriesQuery = useQuery({
    queryKey: ['memories', searchQuery],
    queryFn: () => api.memory.list(searchQuery || undefined),
    staleTime: 30000,
  });

  const personalityProfileQuery = useQuery({
    queryKey: ['personalityProfile'],
    queryFn: () => api.memory.getPersonalityProfile(),
    staleTime: 60000,
  });

  return {
    memories: memoriesQuery.data?.memories ?? [],
    personalityProfile: personalityProfileQuery.data,
    // ...
  };
}
```

### Pagination Example

```typescript
const [offset, setOffset] = useState(0);
const limit = 20;

const { data } = useQuery({
  queryKey: ['memories', offset],
  queryFn: () => api.get(`/csm/memories?limit=${limit}&offset=${offset}`),
});

// Load more
if (data.hasMore) {
  setOffset(data.nextCursor);
}
```

### Search Example

```typescript
const searchMemories = async (query: string) => {
  const response = await api.post('/csm/memories/search', {
    query,
    max_results: 20,
    min_relevance: 0.6,
  });
  return response.data.memories;
};
```

---

## Performance Tips

1. **Caching**: Personality profile changes infrequently, cache for 60s+
2. **Pagination**: Use cursor-based pagination for large lists
3. **Search**: Use text search (`?q=`) for simple queries, semantic search for complex
4. **Debouncing**: Debounce search input to avoid excessive API calls

---

## Migration from Old API

If you were using placeholder endpoints:

**Old:**
```typescript
// This was returning empty arrays
api.memory.list()
```

**New:**
```typescript
// Now returns actual memories
api.memory.list()  // GET /api/v1/csm/memories
```

**URL Changes:**
- ✅ No URL changes needed - paths match frontend expectations
- ✅ Response format matches TypeScript types
- ✅ All features now functional

---

## Testing

### Manual Testing with cURL

```bash
# Get personality profile
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/csm/profile

# List memories
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/csm/memories?limit=10"

# Search memories
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "project deadlines"}' \
  http://localhost:8000/api/v1/csm/memories/search

# Create memory
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test memory", "source": "conversation"}' \
  http://localhost:8000/api/v1/csm/memories
```

---

## Support

For issues or questions:
1. Check error response for details
2. Verify authentication token is valid
3. Ensure user has completed onboarding (CSM profile exists)
4. Check backend logs for detailed error messages
