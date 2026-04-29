/**
 * collections/endpoints/index.ts
 * Barrel export for all custom Payload endpoints.
 *
 * - Global endpoints are registered in payload.config.ts → buildConfig({ endpoints })
 * - Collection endpoints are registered in the collection config → { endpoints }
 */

export { importUrlEndpoint } from './import-url'
export { seedEndpoint } from './seed'
export { syncEngineEndpoint } from './sync-engine'
export { syncCatalogEndpoint } from './sync-catalog'
export { homeMetricsEndpoint } from './home-metrics'
