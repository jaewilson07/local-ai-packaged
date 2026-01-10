import { ImmichAsset, ImmichAssetResponse, ImmichPerson, ImmichFace } from './types'

const IMMICH_API_URL = process.env.IMMICH_API_URL || 'http://immich-server:2283'
const IMMICH_API_KEY = process.env.IMMICH_API_KEY || ''

class ImmichClient {
  private baseUrl: string
  private apiKey: string

  constructor() {
    this.baseUrl = IMMICH_API_URL
    this.apiKey = IMMICH_API_KEY
  }

  private async fetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const response = await fetch(url, {
      ...options,
      headers: {
        'x-api-key': this.apiKey,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      throw new Error(`Immich API error: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  async getRecentAssets(limit: number = 50, skip: number = 0): Promise<ImmichAssetResponse> {
    return this.fetch<ImmichAssetResponse>(
      `/api/asset?limit=${limit}&skip=${skip}&order=DESC`
    )
  }

  async getAssetById(assetId: string): Promise<ImmichAsset> {
    return this.fetch<ImmichAsset>(`/api/asset/${assetId}`)
  }

  async getPeople(): Promise<ImmichPerson[]> {
    return this.fetch<ImmichPerson[]>(`/api/person?withHidden=false`)
  }

  async getPersonById(personId: string): Promise<ImmichPerson> {
    return this.fetch<ImmichPerson>(`/api/person/${personId}`)
  }

  async getPersonAssets(personId: string, limit: number = 50): Promise<ImmichAssetResponse> {
    return this.fetch<ImmichAssetResponse>(
      `/api/person/${personId}/assets?limit=${limit}`
    )
  }

  async getAssetFaces(assetId: string): Promise<ImmichFace[]> {
    try {
      return await this.fetch<ImmichFace[]>(`/api/asset/${assetId}/faces`)
    } catch (error: any) {
      // 404 means no faces detected, return empty array
      if (error.message?.includes('404')) {
        return []
      }
      throw error
    }
  }

  getThumbnailUrl(assetId: string): string {
    return `${this.baseUrl}/api/asset/${assetId}/thumbnail?x-api-key=${this.apiKey}`
  }

  getAssetUrl(assetId: string): string {
    return `${this.baseUrl}/api/asset/${assetId}/file?x-api-key=${this.apiKey}`
  }

  getPersonThumbnailUrl(personId: string): string {
    return `${this.baseUrl}/api/person/${personId}/thumbnail?x-api-key=${this.apiKey}`
  }
}

export const immichClient = new ImmichClient()
