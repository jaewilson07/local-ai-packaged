export interface ImmichAsset {
  id: string
  type: 'IMAGE' | 'VIDEO'
  createdAt: string
  updatedAt: string
  fileCreatedAt: string
  fileModifiedAt: string
  isFavorite: boolean
  isArchived: boolean
  isExternal: boolean
  isOffline: boolean
  isReadOnly: boolean
  duration: string
  exifInfo?: {
    make?: string
    model?: string
    lensModel?: string
    dateTimeOriginal?: string
    exifImageWidth?: number
    exifImageHeight?: number
    latitude?: number
    longitude?: number
    city?: string
    state?: string
    country?: string
  }
  livePhotoVideoId?: string
  originalFileName: string
  resized: boolean
  thumbhash?: string
  encodedVideoPath?: string
  webpPath?: string
  previewPath?: string
  thumbnailPath?: string
  personIds: string[]
}

export interface ImmichPerson {
  id: string
  name: string
  thumbnailPath?: string
  faceAssetId?: string
  faceCount: number
  isHidden: boolean
}

export interface ImmichFace {
  id: string
  personId?: string
  person?: ImmichPerson
  assetId: string
  boundingBoxX1: number
  boundingBoxY1: number
  boundingBoxX2: number
  boundingBoxY2: number
  imageHeight: number
  imageWidth: number
}

export interface ImmichAssetResponse {
  items: ImmichAsset[]
  total: number
}

export interface ImmichPersonResponse {
  id: string
  name: string
  thumbnailPath?: string
  faceAssetId?: string
  faceCount: number
  isHidden: boolean
}
