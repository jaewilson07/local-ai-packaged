'use client'

import { ImmichFace } from '@/lib/immich/types'
import Link from 'next/link'

interface FaceOverlayProps {
  faces: ImmichFace[]
  videoWidth: number
  videoHeight: number
  containerWidth: number
  containerHeight: number
}

export function FaceOverlay({
  faces,
  videoWidth,
  videoHeight,
  containerWidth,
  containerHeight,
}: FaceOverlayProps) {
  const scaleX = containerWidth / videoWidth
  const scaleY = containerHeight / videoHeight

  return (
    <div className="absolute inset-0 pointer-events-none">
      {faces.map((face) => {
        if (!face.person) return null

        const x1 = face.boundingBoxX1 * scaleX
        const y1 = face.boundingBoxY1 * scaleY
        const width = (face.boundingBoxX2 - face.boundingBoxX1) * scaleX
        const height = (face.boundingBoxY2 - face.boundingBoxY1) * scaleY

        return (
          <Link
            key={face.id}
            href={`/discover/${face.personId}`}
            className="absolute border-2 border-blue-500 hover:border-blue-400 transition-colors pointer-events-auto group"
            style={{
              left: `${x1}px`,
              top: `${y1}px`,
              width: `${width}px`,
              height: `${height}px`,
            }}
            title={face.person.name}
          >
            <div className="absolute -top-8 left-0 bg-black/80 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
              {face.person.name}
            </div>
          </Link>
        )
      })}
    </div>
  )
}
