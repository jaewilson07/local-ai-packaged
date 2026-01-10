'use client'

import { useQuery } from '@tanstack/react-query'
import { useParams } from 'next/navigation'
import { PersonAssets } from '@/components/discover/PersonAssets'
import { ImmichAsset } from '@/lib/immich/types'
import Link from 'next/link'

async function fetchPersonAssets(personId: string): Promise<{ items: ImmichAsset[]; total: number }> {
  const response = await fetch(`/api/immich?action=person-assets&personId=${personId}&limit=100`)
  if (!response.ok) throw new Error('Failed to fetch person assets')
  return response.json()
}

async function fetchPerson(personId: string) {
  const response = await fetch(`/api/immich?action=person&personId=${personId}`)
  if (!response.ok) throw new Error('Failed to fetch person')
  return response.json()
}

export default function PersonDetailPage() {
  const params = useParams()
  const personId = params.personId as string

  const { data: person, isLoading: personLoading } = useQuery({
    queryKey: ['person', personId],
    queryFn: () => fetchPerson(personId),
  })

  const { data: assetsData, isLoading: assetsLoading } = useQuery({
    queryKey: ['person-assets', personId],
    queryFn: () => fetchPersonAssets(personId),
  })

  if (personLoading || assetsLoading) {
    return (
      <div className="container mx-auto p-4">
        <div className="text-center">Loading...</div>
      </div>
    )
  }

  if (!person || !assetsData) {
    return (
      <div className="container mx-auto p-4">
        <div className="text-center text-destructive">Person not found</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4">
      <Link href="/discover" className="text-muted-foreground hover:text-foreground mb-4 inline-block">
        ← Back to Discover
      </Link>
      <h1 className="text-3xl font-bold mb-2">{person.name}</h1>
      <p className="text-muted-foreground mb-6">
        {assetsData.total} {assetsData.total === 1 ? 'asset' : 'assets'}
      </p>
      {assetsData.items.length > 0 ? (
        <PersonAssets assets={assetsData.items} />
      ) : (
        <div className="text-center text-muted-foreground">No assets found</div>
      )}
    </div>
  )
}
