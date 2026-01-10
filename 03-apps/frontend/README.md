# Immich Social Frontend

Next.js 14 social media frontend that adds social features (comments, reactions, discovery) on top of Immich's photo/video management system.

## Features

- **Feed Page** (`/feed`): Infinite scroll feed of recent assets from Immich with comments and reactions
- **Discovery Engine** (`/discover`): Browse people detected in photos/videos and view their content
- **Smart Video Player**: Video player with face detection overlays - click faces to navigate to person pages
- **Social Features**: Comments and reactions (heart, fire) stored in PostgreSQL sidecar database
- **Authentication**: Discord OAuth via NextAuth.js

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS + Shadcn UI
- **Database**: PostgreSQL (Supabase) via Prisma ORM
- **Auth**: NextAuth.js with Discord provider
- **State Management**: TanStack Query (React Query)
- **API Integration**: Immich API for assets, people, and face detection

## Setup

### Prerequisites

- Node.js 20+
- Docker (for containerized deployment)
- Access to Immich server
- Supabase PostgreSQL database
- Discord OAuth app credentials

### Environment Variables

Create a `.env.local` file:

```bash
# Database
DATABASE_URL=postgresql://postgres:password@supabase-db:5432/postgres

# NextAuth
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key-here

# Discord OAuth
DISCORD_CLIENT_ID=your-discord-client-id
DISCORD_CLIENT_SECRET=your-discord-client-secret

# Immich API
IMMICH_API_URL=http://immich-server:2283
IMMICH_API_KEY=your-immich-api-key
```

### Development

```bash
# Install dependencies
npm install

# Generate Prisma client
npm run db:generate

# Run database migrations
npm run db:push

# Start development server
npm run dev
```

### Docker Build

```bash
# Build and run via docker-compose (from project root)
python start_services.py --stack apps
```

## Database Schema

The frontend uses a "sidecar" PostgreSQL database (separate from Immich's database) to store social data:

- **posts**: Captions for Immich assets
- **comments**: User comments on assets
- **reactions**: User reactions (heart, fire) on assets

See `prisma/schema.prisma` for the full schema.

## Project Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── api/               # API routes
│   │   ├── auth/          # NextAuth.js routes
│   │   ├── immich/        # Immich API proxy
│   │   └── social/        # Comments & reactions API
│   ├── discover/          # Discovery pages
│   ├── feed/              # Feed page
│   └── layout.tsx         # Root layout
├── components/             # React components
│   ├── discover/          # Discovery components
│   ├── feed/              # Feed components
│   ├── player/            # Video player with face detection
│   └── social/            # Social features (comments, reactions)
├── lib/                   # Utilities
│   ├── immich/           # Immich API client
│   ├── auth.ts           # Auth utilities
│   └── db.ts             # Prisma client
├── hooks/                 # React hooks
└── prisma/               # Prisma schema
```

## API Routes

### Immich Proxy (`/api/immich`)

- `?action=recent&limit=20&skip=0` - Get recent assets
- `?action=people` - Get all people
- `?action=person&personId=xxx` - Get person details
- `?action=person-assets&personId=xxx` - Get assets for a person
- `?action=asset&assetId=xxx` - Get asset details
- `?action=faces&assetId=xxx` - Get face detection data for asset

### Social API (`/api/social`)

- `GET /api/social/comments?immichAssetId=xxx` - Get comments
- `POST /api/social/comments` - Create comment
- `GET /api/social/reactions?immichAssetId=xxx` - Get reactions
- `POST /api/social/reactions` - Create/update reaction
- `DELETE /api/social/reactions?immichAssetId=xxx` - Remove reaction

## Deployment

The frontend is containerized and deployed as part of the `03-apps` stack. See `03-apps/docker-compose.yml` for configuration.

Caddy reverse proxy routes traffic from `frontend.datacrew.space` (or `FRONTEND_HOSTNAME`) to the frontend container on port 3000.
