'use client'

import { ImmichAsset } from '@/lib/immich/types'
import { immichClient } from '@/lib/immich/client'
import Image from 'next/image'
import Link from 'next/link'

interface PersonAssetsProps {
  assets: ImmichAsset[]
}

export function PersonAssets({ assets }: PersonAssetsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {assets.map((asset) => {
        const thumbnailUrl = immichClient.getThumbnailUrl(asset.id)
        const isVideo = asset.type === 'VIDEO'

        return (
          <Link
            key={asset.id}
            href={`/feed?asset=${asset.id}`}
            className="group relative aspect-square rounded-lg overflow-hidden border bg-card hover:border-primary transition-colors"
          >
            <Image
              src={thumbnailUrl}
              alt={asset.originalFileName}
              fill
              className="object-cover group-hover:scale-105 transition-transform"
            />
            {isVideo && (
              <div className="absolute top-2 right-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
                VIDEO
              </div>
            )}
          </Link>
        )
      })}
    </div>
  )
}
