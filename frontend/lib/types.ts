export type OpportunityScore = {
  estimated_resale?: string | number | null;
  estimated_repair_cost?: string | number | null;
  advised_max_buy?: string | number | null;
  potential_profit?: string | number | null;
  confidence?: string | number | null;
  risk?: string | number | null;
  explanations?: string[] | null;
  computed_at?: string | null;
};

export type ListingSummary = {
  id: string;
  ebay_item_id: string;
  title: string | null;
  current_price?: string | number | null;
  currency: string | null;
  web_url: string | null;
  condition_description: string | null;
  buying_options?: string[] | null;
  listing_ended_at?: string | null;
  last_seen_at: string | null;
  first_seen_at?: string | null;
  is_active?: boolean;
  image_urls?: string[] | null;
  watch_model_id?: string | null;
  resolved_brand_id?: string | null;
  resolved_stock_reference_id?: string | null;
  score?: OpportunityScore | null;
};

export type ParsedAttribute = { key: string; value_text: string | null };
export type RepairSignal = {
  signal_type: string;
  matched_text: string | null;
  source_field: string | null;
};

export type ValuedString = { value: string | null; source: string };
export type MoneyWithSource = {
  amount: string | number | null;
  source: string;
};
export type RecordedSale = {
  price: string | number | null;
  recorded_at: string | null;
  source: string;
};
export type CompBand = {
  count: number;
  p25: string | number | null;
  p75: string | number | null;
  low: string | number | null;
  high: string | number | null;
  label: string;
};

/** Stored from WatchBase /prices JSON (EUR list prices). */
export type WatchBasePriceHistory = {
  source?: string;
  currency?: string;
  fetched_at?: string;
  points?: { date: string; amount: string; series: string }[];
};

export type WatchBaseImportResult = {
  canonical_url: string;
  prices_url: string;
  fields_updated: string[];
  price_points: number;
};

/** Proxied WatchBase `/filter/results?q=` (first page). */
export type WatchbaseSearchHit = { url: string; label: string; image_url?: string | null };
export type WatchbaseSearchResponse = {
  query: string;
  items: WatchbaseSearchHit[];
  total: number;
};

export type WatchModelBrief = {
  id: string;
  brand: string;
  model_family?: string | null;
  model_name?: string | null;
  reference?: string | null;
  observed_price_low?: string | number | null;
  observed_price_high?: string | number | null;
  manual_price_low?: string | number | null;
  manual_price_high?: string | number | null;
};

export type WatchModel = WatchModelBrief & {
  /** Active linked eBay listing URLs (GET detail only; list endpoint may omit or empty). */
  linked_ebay_urls?: string[];
  caliber?: string | null;
  image_urls?: string[] | null;
  production_start?: string | null;
  production_end?: string | null;
  description?: string | null;
  reference_url?: string | null;
  /** Exact Everywatch listing page; used first for snapshots and market search. */
  everywatch_url?: string | null;
  spec_case_material?: string | null;
  spec_bezel?: string | null;
  spec_crystal?: string | null;
  spec_case_back?: string | null;
  spec_case_diameter_mm?: string | number | null;
  spec_case_height_mm?: string | number | null;
  spec_lug_width_mm?: string | number | null;
  spec_water_resistance_m?: string | number | null;
  spec_dial_color?: string | null;
  spec_dial_material?: string | null;
  spec_indexes_hands?: string | null;
  external_price_history?: WatchBasePriceHistory | null;
  /** Everywatch + Chrono24 snapshot JSON (server-filled). */
  market_source_snapshots?: Record<string, unknown> | null;
  watchbase_imported_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type WatchModelListResponse = {
  items: WatchModel[];
  total: number;
  skip: number;
  limit: number;
};

export type PromoteWatchCatalogResponse = {
  outcome: string;
  watch_model: WatchModel | null;
};

export type UnifiedMarketHit = {
  url: string;
  label: string;
  image_url?: string | null;
  price_hint?: string | null;
};

export type UnifiedMarketSearchResponse = {
  query: string;
  watchbase: { items: UnifiedMarketHit[]; total: number };
  everywatch: { items: UnifiedMarketHit[] };
  chrono24: {
    items: UnifiedMarketHit[];
    search_url: string;
    google_site_url: string;
    error?: string | null;
  };
};

export type MarketSnapshotsRefreshResponse = {
  ok: boolean;
  skipped?: string | null;
  error?: string | null;
  everywatch_hits: number;
  chrono24_hits: number;
  merged_manual_bounds: boolean;
  everywatch_specs_applied?: boolean;
};

export type BackfillWatchCatalogResponse = {
  scanned: number;
  already_linked: number;
  linked_existing: number;
  created_new: number;
  skipped_no_identity: number;
  queued_for_review?: number;
  skipped_excluded_brand?: number;
};

export type BackfillEntityDictionariesResponse = {
  scanned: number;
  with_resolved_brand: number;
  with_resolved_reference: number;
  with_caliber_link: number;
  inferred_brand: number;
};

export type WatchLinkReviewBrief = {
  id: string;
  tier?: string | null;
  confidence?: string | number | null;
  candidate_count: number;
  reason_codes?: string[] | null;
};

export type WatchLinkReviewListItem = {
  id: string;
  listing_id: string;
  ebay_item_id: string;
  listing_title?: string | null;
  listing_description?: string | null;
  listing_web_url?: string | null;
  listing_image_urls?: string[] | null;
  listing_ended_at?: string | null;
  buying_options?: string[] | null;
  tier?: string | null;
  confidence?: string | number | null;
  candidate_count: number;
  reason_codes?: string[] | null;
  created_at?: string | null;
};

export type WatchLinkReviewListResponse = {
  items: WatchLinkReviewListItem[];
  total: number;
};

export type WatchLinkReviewDetail = {
  id: string;
  listing_id: string;
  ebay_item_id: string;
  listing_title?: string | null;
  listing_description?: string | null;
  listing_web_url?: string | null;
  listing_image_urls?: string[] | null;
  listing_ended_at?: string | null;
  buying_options?: string[] | null;
  tier?: string | null;
  confidence?: string | number | null;
  reason_codes?: string[] | null;
  candidate_watch_models: WatchModel[];
  candidate_scores: Record<string, number>;
  created_at?: string | null;
};

export type ListingDetail = ListingSummary & {
  subtitle?: string | null;
  image_urls?: string[] | null;
  shipping_price?: string | number | null;
  seller_username?: string | null;
  category_path?: string | null;
  is_active?: boolean;
  parsed_attributes: ParsedAttribute[];
  repair_signals: RepairSignal[];
  opportunity_scores: OpportunityScore[];
  brand: ValuedString;
  model_family: ValuedString;
  reference: ValuedString;
  caliber: ValuedString;
  repair_supplement: MoneyWithSource;
  donor_cost: MoneyWithSource;
  recorded_sale: RecordedSale;
  notes: string | null;
  comp_sales: CompBand;
  comp_asking: CompBand;
  source_legend: Record<string, string>;
  field_guidance: Record<string, string>;
  watch_model_id?: string | null;
  watch_model?: WatchModelBrief | null;
  watch_link_review_pending?: WatchLinkReviewBrief | null;
};

export type ListingListResponse = {
  items: ListingSummary[];
  total: number;
  skip: number;
  limit: number;
};

export type DashboardStats = {
  total_listings: number;
  active_listings: number;
  candidate_count: number;
  listings_with_repair_signals: number;
  recent_listings: ListingSummary[];
  ebay_browse_search_calls?: number;
  ebay_oauth_token_calls?: number;
  ebay_browse_get_item_calls?: number;
};

export type IngestQueryDto = {
  id: string;
  label: string;
  query: string;
  enabled: boolean;
};

export type AppSettings = {
  ingest_interval_minutes: number;
  ebay_search_limit: number;
  ingest_max_pages: number;
  ingest_queries: IngestQueryDto[];
  env_fallback_query: string;
  watch_catalog_review_mode?: string;
  /** Comma-separated excluded words/phrases; merged with server env WATCH_CATALOG_EXCLUDED_BRANDS */
  watch_catalog_excluded_brands?: string;
  everywatch_login_email?: string;
  everywatch_password_configured?: boolean;
  stale_listing_refresh_enabled?: boolean;
  stale_listing_refresh_interval_minutes?: number;
  stale_listing_refresh_max_per_run?: number;
  stale_listing_refresh_min_age_hours?: number;
  /** 0 = no scheduled job; otherwise minutes between re-processing unmatched listings for the match queue */
  match_queue_sync_interval_minutes?: number;
  /** Whether queue requires parsed brand + reference/family identity before enqueueing */
  watch_catalog_queue_require_identity?: boolean;
};

export type ActiveRefreshStatus = {
  running: boolean;
  total: number;
  processed: number;
  updated: number;
  ended: number;
  errors: number;
  current_item_id?: string | null;
  current_index: number;
  last_status?: string | null;
  last_error?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
};

export type NotInterestedItem = {
  id: string;
  ebay_item_id: string;
  source?: string | null;
  reason?: string | null;
  note?: string | null;
  last_listing_title?: string | null;
  last_listing_web_url?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  restored_at?: string | null;
};

export type NotInterestedListResponse = {
  items: NotInterestedItem[];
  total: number;
};

export type EverywatchDebugFetchRow = {
  url: string;
  status_code: number | null;
  error: string | null;
  html_received: boolean;
  analysis: Record<string, unknown> | null;
};

export type EverywatchDebugResponse = {
  watch_model_brief: Record<string, unknown> | null;
  urls_attempted: string[];
  collect_everywatch_snapshot: Record<string, unknown> | null;
  fetches: EverywatchDebugFetchRow[];
  login_attempt?: Record<string, unknown> | null;
};

/** Client-only row key + editable fields */
export type IngestQueryLine = {
  clientKey: string;
  label: string;
  query: string;
  enabled: boolean;
};
