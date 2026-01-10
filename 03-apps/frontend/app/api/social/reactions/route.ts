import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth/next'
import { authOptions } from '@/app/api/auth/[...nextauth]/route'
import { db } from '@/lib/db'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const immichAssetId = searchParams.get('immichAssetId')

  if (!immichAssetId) {
    return NextResponse.json({ error: 'immichAssetId required' }, { status: 400 })
  }

  try {
    const reactions = await db.reaction.findMany({
      where: { immichAssetId },
    })

    return NextResponse.json(reactions)
  } catch (error: any) {
    console.error('Error fetching reactions:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions)

  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const body = await request.json()
    const { immichAssetId, type } = body

    if (!immichAssetId || !type) {
      return NextResponse.json(
        { error: 'immichAssetId and type required' },
        { status: 400 }
      )
    }

    if (type !== 'heart' && type !== 'fire') {
      return NextResponse.json(
        { error: 'type must be "heart" or "fire"' },
        { status: 400 }
      )
    }

    // Upsert reaction (create or update)
    const reaction = await db.reaction.upsert({
      where: {
        immichAssetId_userId: {
          immichAssetId,
          userId: session.user.id,
        },
      },
      update: {
        type,
      },
      create: {
        immichAssetId,
        userId: session.user.id,
        type,
      },
    })

    return NextResponse.json(reaction, { status: 201 })
  } catch (error: any) {
    console.error('Error creating reaction:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function DELETE(request: NextRequest) {
  const session = await getServerSession(authOptions)

  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const searchParams = request.nextUrl.searchParams
    const immichAssetId = searchParams.get('immichAssetId')

    if (!immichAssetId) {
      return NextResponse.json(
        { error: 'immichAssetId required' },
        { status: 400 }
      )
    }

    await db.reaction.delete({
      where: {
        immichAssetId_userId: {
          immichAssetId,
          userId: session.user.id,
        },
      },
    })

    return NextResponse.json({ success: true })
  } catch (error: any) {
    console.error('Error deleting reaction:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
