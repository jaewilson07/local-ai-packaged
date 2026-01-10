import { NextRequest, NextResponse } from 'next/server'
import { immichClient } from '@/lib/immich/client'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const action = searchParams.get('action')

  try {
    switch (action) {
      case 'recent':
        const limit = parseInt(searchParams.get('limit') || '50')
        const skip = parseInt(searchParams.get('skip') || '0')
        const assets = await immichClient.getRecentAssets(limit, skip)
        return NextResponse.json(assets)

      case 'people':
        const people = await immichClient.getPeople()
        return NextResponse.json(people)

      case 'person':
        const personId = searchParams.get('personId')
        if (!personId) {
          return NextResponse.json({ error: 'personId required' }, { status: 400 })
        }
        const person = await immichClient.getPersonById(personId)
        return NextResponse.json(person)

      case 'person-assets':
        const personIdForAssets = searchParams.get('personId')
        if (!personIdForAssets) {
          return NextResponse.json({ error: 'personId required' }, { status: 400 })
        }
        const personLimit = parseInt(searchParams.get('limit') || '50')
        const personAssets = await immichClient.getPersonAssets(personIdForAssets, personLimit)
        return NextResponse.json(personAssets)

      case 'asset':
        const assetId = searchParams.get('assetId')
        if (!assetId) {
          return NextResponse.json({ error: 'assetId required' }, { status: 400 })
        }
        const asset = await immichClient.getAssetById(assetId)
        return NextResponse.json(asset)

      case 'faces':
        const faceAssetId = searchParams.get('assetId')
        if (!faceAssetId) {
          return NextResponse.json({ error: 'assetId required' }, { status: 400 })
        }
        const faces = await immichClient.getAssetFaces(faceAssetId)
        return NextResponse.json(faces)

      default:
        return NextResponse.json({ error: 'Invalid action' }, { status: 400 })
    }
  } catch (error: any) {
    console.error('Immich API error:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
