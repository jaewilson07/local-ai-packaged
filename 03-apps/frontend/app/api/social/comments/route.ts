import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth/next'
import { authOptions } from '@/app/api/auth/config'
import { db } from '@/lib/db'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const immichAssetId = searchParams.get('immichAssetId')

  if (!immichAssetId) {
    return NextResponse.json({ error: 'immichAssetId required' }, { status: 400 })
  }

  try {
    const comments = await db.comment.findMany({
      where: { immichAssetId },
      orderBy: { createdAt: 'desc' },
    })

    return NextResponse.json(comments)
  } catch (error: any) {
    console.error('Error fetching comments:', error)
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
    const { immichAssetId, text } = body

    if (!immichAssetId || !text) {
      return NextResponse.json(
        { error: 'immichAssetId and text required' },
        { status: 400 }
      )
    }

    const comment = await db.comment.create({
      data: {
        immichAssetId,
        userId: session.user.id,
        text,
      },
    })

    return NextResponse.json(comment, { status: 201 })
  } catch (error: any) {
    console.error('Error creating comment:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
