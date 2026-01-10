'use client'

import { ImmichPerson } from '@/lib/immich/types'
import { immichClient } from '@/lib/immich/client'
import Image from 'next/image'
import Link from 'next/link'

interface PersonGridProps {
  people: ImmichPerson[]
}

export function PersonGrid({ people }: PersonGridProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
      {people.map((person) => {
        const thumbnailUrl = person.thumbnailPath
          ? immichClient.getPersonThumbnailUrl(person.id)
          : 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2RkZCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5ObyBJbWFnZTwvdGV4dD48L3N2Zz4='

        return (
          <Link
            key={person.id}
            href={`/discover/${person.id}`}
            className="group relative aspect-square rounded-lg overflow-hidden border bg-card hover:border-primary transition-colors"
          >
            <Image
              src={thumbnailUrl}
              alt={person.name}
              fill
              className="object-cover group-hover:scale-105 transition-transform"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent flex items-end">
              <p className="text-white font-medium p-2 w-full truncate">{person.name}</p>
            </div>
          </Link>
        )
      })}
    </div>
  )
}
