'use client'

import { useQuery } from '@tanstack/react-query'
import { PersonGrid } from '@/components/discover/PersonGrid'
import { ImmichPerson } from '@/lib/immich/types'

async function fetchPeople(): Promise<ImmichPerson[]> {
  const response = await fetch('/api/immich?action=people')
  if (!response.ok) throw new Error('Failed to fetch people')
  return response.json()
}

export default function DiscoverPage() {
  const { data: people, isLoading, isError } = useQuery({
    queryKey: ['people'],
    queryFn: fetchPeople,
  })

  if (isLoading) {
    return (
      <div className="container mx-auto p-4">
        <div className="text-center">Loading...</div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="container mx-auto p-4">
        <div className="text-center text-destructive">Error loading people</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-2">Who are you looking for?</h1>
      <p className="text-muted-foreground mb-6">Click on a face to see their photos and videos</p>
      {people && people.length > 0 ? (
        <PersonGrid people={people} />
      ) : (
        <div className="text-center text-muted-foreground">No people found</div>
      )}
    </div>
  )
}
