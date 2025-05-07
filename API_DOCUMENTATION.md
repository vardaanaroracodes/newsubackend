# NewsU Backend API Documentation

## Authentication

All endpoints in this API require API key authentication. Include the API key in your request headers:

```
API-AUTH-KEY: your-super-secret-api-key-123
```

## API Routes Overview

The API is organized into several modules:

1. **News Agent Routes** - AI-powered news search and conversation
2. **Session Management Routes** - Managing persistent chat sessions
3. **News Tracking Routes** - Monitoring specific news topics over time

## 1. News Agent Routes

### 1.1. `/api/news/ask` (POST)

Makes a direct question to the AI news agent.

**Request:**
```json
{
  "query": "What are the latest developments in AI?"
}
```

**Response:**
```json
{
  "success": true,
  "response": "Recent AI developments include...",
  "sources": [
    {
      "title": "New AI Breakthrough",
      "link": "https://example.com/article",
      "source": "Tech Journal",
      "date": "2025-04-30",
      "snippet": "Researchers have made significant strides..."
    }
  ]
}
```

### 1.2. `/api/news/clear` (POST)

Clears the conversation history in the default agent.

**Request:** Empty body

**Response:**
```json
{
  "success": true,
  "message": "Conversation history cleared"
}
```

### 1.3. `/api/news/history` (GET)

Retrieves the conversation history for the default agent.

**Response:**
```json
{
  "success": true,
  "history": [
    {
      "role": "user",
      "content": "Tell me about recent space discoveries"
    },
    {
      "role": "ai", 
      "content": "Recent space discoveries include..."
    }
  ]
}
```

## 2. Session Management Routes

### 2.1. `/api/news/session/start` (POST)

Creates a new chat session with a unique ID.

**Request:**
```json
{
  "user_id": "user123"
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 2.2. `/api/news/session/{session_id}/ask` (POST)

Makes a query within a specific session, maintaining conversation context.

**Request:**
```json
{
  "user_id": "user123",
  "query": "What are the latest developments in AI?"
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "response": "Recent AI developments include...",
  "sources": [/* Same format as /ask endpoint */]
}
```

### 2.3. `/api/news/sessions` (GET)

Lists all sessions for a specific user.

**Query Parameters:**
- `user_id` (required): The user's ID

**Response:**
```json
{
  "success": true,
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-04-30T10:30:00Z"
    }
  ]
}
```

### 2.4. `/api/news/session/{session_id}/history` (GET)

Gets the conversation history for a specific session.

**Query Parameters:**
- `user_id` (required): The user's ID

**Response:**
```json
{
  "success": true,
  "history": [
    {
      "role": "user",
      "content": "What are the latest developments in AI?",
      "timestamp": "2025-04-30T10:30:00Z"
    },
    {
      "role": "ai",
      "content": "Recent AI developments include...",
      "timestamp": "2025-04-30T10:30:05Z"
    }
  ]
}
```

### 2.5. `/api/news/session/{session_id}/clear` (POST)

Clears the conversation history for a specific session.

**Request:**
```json
{
  "user_id": "user123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Session cleared"
}
```

### 2.6. `/api/news/session/{session_id}/delete` (DELETE)

Completely deletes a session and its history.

**Request:**
```json
{
  "user_id": "user123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Session deleted"
}
```

## 3. News Tracking Routes

### 3.1. `/api/news/tracked-queries` (GET)

Gets all tracked news queries for a specific user.

**Query Parameters:**
- `user_id` (required): The user's ID

**Response:**
```json
{
  "success": true,
  "tracked_queries": [
    {
      "_id": "60a1f2b3c4d5e6f7g8h9i0j1",
      "query": "artificial intelligence latest developments",
      "is_active": true,
      "created_at": "2025-04-25T08:08:51.769Z",
      "updated_at": "2025-04-30T08:12:15.392Z"
    }
  ],
  "count": 1
}
```

### 3.2. `/api/news/tracked-queries/{query_id}` (GET)

Gets detailed information about a specific tracked query.

**Query Parameters:**
- `user_id` (required): The user's ID
- `include_history` (optional, default: true): Whether to include tracking history

**Response:**
```json
{
  "success": true,
  "tracked_query": {
    "_id": "60a1f2b3c4d5e6f7g8h9i0j1",
    "user_id": "user456",
    "query": "artificial intelligence latest developments",
    "is_active": true,
    "created_at": "2025-04-25T08:08:51.769Z",
    "updated_at": "2025-04-30T08:12:15.392Z",
    "tracking_history": [
      {
        "date": "2025-04-30T08:12:15.392Z",
        "summary": "Recent breakthroughs in artificial intelligence include...",
        "sources": {
          "Artificial Intelligence News - ScienceDaily": {
            "link": "https://www.sciencedaily.com/news/computers_math/artificial_intelligence/",
            "snippet": "Latest Headlines...",
            "position": 1
          }
        },
        "changes": {
          "new": "Other significant developments include...",
          "removed": "Recent breakthroughs in artificial intelligence..."
        }
      }
    ]
  }
}
```

### 3.3. `/api/news/tracked-queries` (POST)

Creates a new tracked query for a user.

**Request:**
```json
{
  "user_id": "user456",
  "query": "artificial intelligence latest developments"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Tracked query created successfully",
  "tracked_query_id": "60a1f2b3c4d5e6f7g8h9i0j1"
}
```

### 3.4. `/api/news/tracked-queries/{query_id}` (PATCH)

Updates the status of a tracked query.

**Request:**
```json
{
  "user_id": "user456",
  "is_active": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Tracked query updated successfully"
}
```

### 3.5. `/api/news/tracked-queries/{query_id}` (DELETE)

Deletes a tracked query.

**Request:**
```json
{
  "user_id": "user456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Tracked query deleted successfully"
}
```

## System Flow

### 1. News Agent Flow

```
User Query → API Authentication → NewsAgentService → 
Gemini AI + Serper Search → Response Generation → 
JSON Response with AI Summary and Sources
```

1. User sends a query to `/api/news/ask` endpoint
2. The system authenticates the API key
3. The query is passed to the NewsAgentService
4. Gemini AI processes the query and uses Serper API to search for relevant news
5. LangChain combines the search results and generates a summary response
6. The system returns the AI-generated response with source articles

### 2. Session Management Flow

```
Session Creation → Query in Session Context → 
Load Previous Messages → Generate Response → 
Store Conversation → Return Response
```

1. User creates a session with their user ID
2. User sends a query within that session
3. System loads the existing conversation history
4. The query is processed in the context of the previous conversation
5. Response and conversation history are saved to MongoDB
6. The system returns the response with session information

### 3. News Tracking Flow

```
Create Tracking Query → Store in MongoDB → 
Periodic Updates (Background Job) → 
Query Retrieval with History
```

1. User creates a news tracking query
2. The system stores it in MongoDB with empty tracking history
3. A background job (not shown in the code) updates the tracking history periodically
4. User can retrieve their tracked queries with complete history of changes

## Database Structure

The application uses MongoDB with two databases:
1. `newsu` - Main database for user sessions and basic application data
   - `chat_sessions` collection - Stores chat sessions and conversation history
2. `news_tracker` - Separate database for news tracking functionality
   - `tracked_queries` collection - Stores tracking queries and their history

## Error Handling

All endpoints have consistent error handling:
- Missing required fields return 400 Bad Request
- Authentication failures return 401 Unauthorized
- Access to unauthorized resources returns 403 Forbidden
- Non-existent resources return 404 Not Found
- Internal errors return 500 Internal Server Error with error details

All responses follow a consistent format:
```json
{
  "success": true/false,
  "message/error": "Description",
  "details": "Error details (only on error)"
}
```