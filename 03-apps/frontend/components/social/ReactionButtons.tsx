'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSession } from 'next-auth/react'
import { Button } from '@/components/ui/button'
import { Heart, Flame } from 'lucide-react'

interface Reaction {
  immichAssetId: string
  userId: string
  type: 'heart' | 'fire'
}

interface ReactionButtonsProps {
  immichAssetId: string
}

export function ReactionButtons({ immichAssetId }: ReactionButtonsProps) {
  const { data: session } = useSession()
  const queryClient = useQueryClient()
  const [userReaction, setUserReaction] = useState<'heart' | 'fire' | null>(null)

  const { data: reactions = [] } = useQuery<Reaction[]>({
    queryKey: ['reactions', immichAssetId],
    queryFn: async () => {
      const response = await fetch(`/api/social/reactions?immichAssetId=${immichAssetId}`)
      if (!response.ok) throw new Error('Failed to fetch reactions')
      return response.json()
    },
  })

  useEffect(() => {
    if (session?.user?.id && reactions.length > 0) {
      const userReact = reactions.find((r) => r.userId === session.user.id)
      setUserReaction(userReact?.type || null)
    }
  }, [reactions, session?.user?.id])

  const heartCount = reactions.filter((r) => r.type === 'heart').length
  const fireCount = reactions.filter((r) => r.type === 'fire').length

  const toggleReaction = useMutation({
    mutationFn: async (type: 'heart' | 'fire') => {
      if (userReaction === type) {
        // Remove reaction
        const response = await fetch(
          `/api/social/reactions?immichAssetId=${immichAssetId}`,
          { method: 'DELETE' }
        )
        if (!response.ok) throw new Error('Failed to delete reaction')
        return null
      } else {
        // Add or change reaction
        const response = await fetch('/api/social/reactions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ immichAssetId, type }),
        })
        if (!response.ok) throw new Error('Failed to create reaction')
        return response.json()
      }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['reactions', immichAssetId] })
      if (data) {
        setUserReaction(data.type)
      } else {
        setUserReaction(null)
      }
    },
  })

  return (
    <div className="flex gap-2">
      <Button
        variant={userReaction === 'heart' ? 'default' : 'outline'}
        size="sm"
        onClick={() => session && toggleReaction.mutate('heart')}
        disabled={!session}
      >
        <Heart className="w-4 h-4 mr-1" />
        {heartCount}
      </Button>
      <Button
        variant={userReaction === 'fire' ? 'default' : 'outline'}
        size="sm"
        onClick={() => session && toggleReaction.mutate('fire')}
        disabled={!session}
      >
        <Flame className="w-4 h-4 mr-1" />
        {fireCount}
      </Button>
    </div>
  )
}
