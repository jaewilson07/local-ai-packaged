# Immich API Integration Notes

This document contains notes about Immich API integration for the Discord bot.

## Authentication

All API requests require the `x-api-key` header:

```python
headers = {"x-api-key": IMMICH_API_KEY}
```

## Endpoints Used

### Upload Asset

**Endpoint**: `POST /api/asset/upload`

**Headers**:
- `x-api-key: {IMMICH_API_KEY}`

**Body**: `multipart/form-data`
- `assetData`: File bytes
- `description` (optional): Asset description

**Response**: Asset metadata with `id` field

### Search People

**Endpoint**: `GET /api/person`

**Headers**:
- `x-api-key: {IMMICH_API_KEY}`

**Query Parameters**:
- `withHidden`: `false` (exclude hidden people)

**Response**: Array of person objects with:
- `id`: Person ID
- `name`: Person name
- `thumbnailPath`: Thumbnail path (relative)

**Note**: Immich doesn't have a direct search endpoint, so we fetch all people and filter client-side.

### Get Person Thumbnail

**Endpoint**: `GET /api/person/{personId}/thumbnail`

**Headers**:
- `x-api-key: {IMMICH_API_KEY}` (as query parameter: `?x-api-key=...`)

**Response**: Image binary

### Get Asset Faces

**Endpoint**: `GET /api/asset/{assetId}/faces`

**Headers**:
- `x-api-key: {IMMICH_API_KEY}`

**Response**: Array of face objects with:
- `personId`: Associated person ID (if recognized)
- `boundingBox`: Face coordinates

**Note**: Returns 404 if no faces detected.

### List New Assets

**Endpoint**: `GET /api/asset`

**Headers**:
- `x-api-key: {IMMICH_API_KEY}`

**Query Parameters**:
- `updatedAfter`: ISO timestamp (e.g., `2024-01-01T00:00:00.000Z`)

**Response**: Paginated response with `items` array containing asset objects

### Get Asset Thumbnail

**Endpoint**: `GET /api/asset/{assetId}/thumbnail`

**Headers**:
- `x-api-key: {IMMICH_API_KEY}` (as query parameter: `?x-api-key=...`)

**Response**: Image binary

## Error Handling

- **401 Unauthorized**: Invalid or missing API key
- **404 Not Found**: Resource doesn't exist (e.g., no faces detected)
- **500 Internal Server Error**: Immich server error

## Rate Limiting

Immich may rate limit requests. The bot implements:
- Retry logic with exponential backoff
- 2-minute polling interval for notifications
- Error logging for failed requests

## References

- [Immich API Documentation](https://immich.app/docs/api)
- [Immich GitHub](https://github.com/immich-app/immich)
