import { GrowthBook } from '@growthbook/growthbook'
import { identify } from './identify'

// Local feature flag definitions — no external API calls
// 本地功能旗標定義 — 不發出任何外部 API 請求
const LOCAL_FEATURES: Record<string, { defaultValue: unknown }> = {
  summer_sale: { defaultValue: false },
  free_delivery: { defaultValue: false },
  proceed_to_checkout: { defaultValue: 'blue' },
}

// Initialize GrowthBook instance
let growthbook: GrowthBook | null = null
let dummyGrowthBook: GrowthBook | null = null

export function getGrowthBook(): GrowthBook {
  if (typeof window === 'undefined') {
    // Server-side: return a cached local GrowthBook instance
    if (!dummyGrowthBook) {
      dummyGrowthBook = new GrowthBook({
        attributes: {},
        features: LOCAL_FEATURES,
      })
    }
    return dummyGrowthBook
  }

  if (!growthbook) {
    // Closed-loop mode: load flags from local definitions only, no external CDN
    // 閉環模式：僅從本地定義載入旗標，不連接外部 CDN
    growthbook = new GrowthBook({
      enableDevMode: process.env.NODE_ENV === 'development',
      features: LOCAL_FEATURES,
      trackingCallback: (experiment, result) => {
        console.log('Experiment Viewed', {
          experimentId: experiment.key,
          variationId: result.key,
        })
      },
    })

    // Set user attributes
    const attributes = identify()
    growthbook.setAttributes(attributes)
  }

  return growthbook
}

// Feature flag helper functions
export function isFeatureOn(featureKey: string): boolean {
  const gb = getGrowthBook()
  return gb.isOn(featureKey)
}

export function getFeatureValue<T>(featureKey: string, defaultValue: T): T {
  const gb = getGrowthBook()
  // Type assertion is necessary because GrowthBook's getFeatureValue returns WidenPrimitives<T>
  // which widens primitive types (e.g., "blue" becomes string). We assert back to T to maintain
  // the specific type from the defaultValue parameter.
  // GrowthBook's getFeatureValue is typed to return WidenPrimitives<T>,
  // which intentionally "widens" primitive types for flexibility.
  // Here we expose a simpler helper that returns the same shape as the
  // provided defaultValue, so we assert back to T. This keeps the
  // external API ergonomic while relying on GrowthBook's runtime behavior
  // and the defaultValue type to ensure correctness.
  return gb.getFeatureValue(featureKey, defaultValue) as T
}

// Flag definitions
export const FLAGS = {
  SHOW_SUMMER_SALE: 'summer_sale',
  SHOW_FREE_DELIVERY: 'free_delivery',
  PROCEED_TO_CHECKOUT_COLOR: 'proceed_to_checkout',
} as const
