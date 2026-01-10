'use client'

import { useInfiniteQuery } from '@tanstack/react-query'
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll'
import { AssetCard } from '@/components/feed/AssetCard'
import { ImmichAsset } from '@/lib/immich/types'

async function fetchAssets(page: number = 0): Promise<{ items: ImmichAsset[]; total: number }> {
  const limit = 20
  const skip = page * limit
  const response = await fetch(`/api/immich?action=recent&limit=${limit}&skip=${skip}`)
  if (!response.ok) throw new Error('Failed to fetch assets')
  return response.json()
}

export default function FeedPage() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
  } = useInfiniteQuery({
    queryKey: ['assets'],
    queryFn: ({ pageParam = 0 }) => fetchAssets(pageParam),
    getNextPageParam: (lastPage, allPages) => {
      const totalFetched = allPages.reduce((sum, page) => sum + page.items.length, 0)
      return totalFetched < lastPage.total ? allPages.length : undefined
    },
    initialPageParam: 0,
  })

  const { lastElementRef } = useInfiniteScroll({
    hasNextPage: !!hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
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
        <div className="text-center text-destructive">Error loading feed</div>
      </div>
    )
  }

  const assets = data?.pages.flatMap((page) => page.items) ?? []

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Feed</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {assets.map((asset, index) => (
          <div
            key={asset.id}
            ref={index === assets.length - 1 ? lastElementRef : null}
          >
            <AssetCard asset={asset} />
          </div>
        ))}
      </div>
      {isFetchingNextPage && (
        <div className="text-center mt-4">Loading more...</div>
      )}
    </div>
  )
}
