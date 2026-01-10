'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSession } from 'next-auth/react'
import { Button } from '@/components/ui/button'

interface Comment {
  id: string
  text: string
  userId: string
  createdAt: string
}

interface CommentSectionProps {
  immichAssetId: string
}

export function CommentSection({ immichAssetId }: CommentSectionProps) {
  const { data: session } = useSession()
  const queryClient = useQueryClient()
  const [commentText, setCommentText] = useState('')

  const { data: comments = [] } = useQuery<Comment[]>({
    queryKey: ['comments', immichAssetId],
    queryFn: async () => {
      const response = await fetch(`/api/social/comments?immichAssetId=${immichAssetId}`)
      if (!response.ok) throw new Error('Failed to fetch comments')
      return response.json()
    },
  })

  const createComment = useMutation({
    mutationFn: async (text: string) => {
      const response = await fetch('/api/social/comments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ immichAssetId, text }),
      })
      if (!response.ok) throw new Error('Failed to create comment')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['comments', immichAssetId] })
      setCommentText('')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (commentText.trim() && session) {
      createComment.mutate(commentText.trim())
    }
  }

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium">Comments</div>
      {comments.length > 0 && (
        <div className="space-y-2 max-h-32 overflow-y-auto">
          {comments.map((comment) => (
            <div key={comment.id} className="text-sm">
              <p className="font-medium">{comment.userId}</p>
              <p className="text-muted-foreground">{comment.text}</p>
            </div>
          ))}
        </div>
      )}
      {session && (
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            placeholder="Add a comment..."
            className="flex-1 px-3 py-2 text-sm border rounded-md"
          />
          <Button type="submit" size="sm" disabled={!commentText.trim()}>
            Post
          </Button>
        </form>
      )}
    </div>
  )
}
