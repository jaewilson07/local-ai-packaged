'use client'

import { ImmichAsset } from '@/lib/immich/types'
import { immichClient } from '@/lib/immich/client'
import Image from 'next/image'
import { SmartPlayer } from '@/components/player/SmartPlayer'
import { CommentSection } from '@/components/social/CommentSection'
import { ReactionButtons } from '@/components/social/ReactionButtons'

interface AssetCardProps {
  asset: ImmichAsset
}

export function AssetCard({ asset }: AssetCardProps) {
  const isVideo = asset.type === 'VIDEO'
  const thumbnailUrl = immichClient.getThumbnailUrl(asset.id)

  return (
    <div className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden">
      <div className="relative aspect-square w-full">
        {isVideo ? (
          <SmartPlayer asset={asset} />
        ) : (
          <Image
            src={thumbnailUrl}
            alt={asset.originalFileName}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        )}
      </div>
      <div className="p-4 space-y-4">
        <ReactionButtons immichAssetId={asset.id} />
        <CommentSection immichAssetId={asset.id} />
      </div>
    </div>
  )
}
