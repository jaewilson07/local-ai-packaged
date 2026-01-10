import { useState, useEffect } from 'react'
import { ImmichFace } from '@/lib/immich/types'

export function useFaceDetection(assetId: string | null) {
  const [faces, setFaces] = useState<ImmichFace[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!assetId) {
      setFaces([])
      return
    }

    setLoading(true)
    setError(null)

    fetch(`/api/immich?action=faces&assetId=${assetId}`)
      .then((res) => {
        if (!res.ok) {
          if (res.status === 404) {
            // No faces detected is not an error
            return []
          }
          throw new Error('Failed to fetch faces')
        }
        return res.json()
      })
      .then((data) => {
        setFaces(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err)
        setLoading(false)
      })
  }, [assetId])

  return { faces, loading, error }
}
