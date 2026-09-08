export interface Weather {
  temp: number
  precip_prob: number
  sky: number
  sky_text: string
  dust: number
}

export interface Scores {
  outdoor: number
  photo: number
  indoor: number
}

export interface Destination {
  name: string
  address: string
  tags: string[]
  score: number
  weather_score: number
  distance_km: number
  image?: string
  copy: string
  category?: string
  coords?: { lat: number; lng: number }
}

export interface PlaceReview {
  author: string
  rating: number
  text: string
  relative: string
}

export interface NextPlace {
  name: string
  address: string
  rating: number
  review_count: number
  open_now: boolean | null
  photo_url: string | null
  types: string[]
  lat: number
  lng: number
  reviews: PlaceReview[]
  website: string
  google_maps: string
}

export interface RecommendResponse {
  city: string
  weather: Weather
  scores: Scores
  total_fetched: number
  recommendations: Destination[]
}
