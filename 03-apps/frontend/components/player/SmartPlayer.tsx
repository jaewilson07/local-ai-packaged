'use client'

import { useState, useRef, useEffect } from 'react'
import { ImmichAsset } from '@/lib/immich/types'
import { immichClient } from '@/lib/immich/client'
import { useFaceDetection } from '@/hooks/useFaceDetection'
import { FaceOverlay } from './FaceOverlay'
import Image from 'next/image'

interface SmartPlayerProps {
  asset: ImmichAsset
}

export function SmartPlayer({ asset }: SmartPlayerProps) {
  const [isHovered, setIsHovered] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [videoDimensions, setVideoDimensions] = useState({ width: 0, height: 0 })
  const [containerDimensions, setContainerDimensions] = useState({ width: 0, height: 0 })
  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const thumbnailUrl = immichClient.getThumbnailUrl(asset.id)
  const videoUrl = immichClient.getAssetUrl(asset.id)

  const { faces, loading: facesLoading } = useFaceDetection(isPlaying ? asset.id : null)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    if (isHovered && !isPlaying) {
      video.play().catch(() => {
        // Auto-play failed, ignore
      })
      setIsPlaying(true)
    } else if (!isHovered && isPlaying) {
      video.pause()
      setIsPlaying(false)
    }
  }, [isHovered, isPlaying])

  useEffect(() => {
    const video = videoRef.current
    const container = containerRef.current

    if (!video || !container) return

    const updateDimensions = () => {
      setVideoDimensions({
        width: video.videoWidth || 0,
        height: video.videoHeight || 0,
      })
      setContainerDimensions({
        width: container.clientWidth,
        height: container.clientHeight,
      })
    }

    video.addEventListener('loadedmetadata', updateDimensions)
    window.addEventListener('resize', updateDimensions)
    updateDimensions()

    return () => {
      video.removeEventListener('loadedmetadata', updateDimensions)
      window.removeEventListener('resize', updateDimensions)
    }
  }, [isPlaying])

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {!isPlaying && (
        <Image
          src={thumbnailUrl}
          alt={asset.originalFileName}
          fill
          className="object-cover"
        />
      )}
      <video
        ref={videoRef}
        src={videoUrl}
        className={`absolute inset-0 w-full h-full object-cover ${
          isPlaying ? 'block' : 'hidden'
        }`}
        loop
        muted
        playsInline
      />
      {isPlaying && !facesLoading && faces.length > 0 && videoDimensions.width > 0 && (
        <FaceOverlay
          faces={faces}
          videoWidth={videoDimensions.width}
          videoHeight={videoDimensions.height}
          containerWidth={containerDimensions.width}
          containerHeight={containerDimensions.height}
        />
      )}
    </div>
  )
}
