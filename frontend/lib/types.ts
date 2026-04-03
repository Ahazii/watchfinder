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
  last_seen_at: string | null;
  is_active?: boolean;
  image_urls?: string[] | null;
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
  caliber?: string | null;
  image_urls?: string[] | null;
  production_start?: string | null;
  production_end?: string | null;
  description?: string | null;
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

export type BackfillWatchCatalogResponse = {
  scanned: number;
  already_linked: number;
  linked_existing: number;
  created_new: number;
  skipped_no_identity: number;
  queued_for_review?: number;
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
  listing_web_url?: string | null;
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
  first_seen_at?: string | null;
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
};

/** Client-only row key + editable fields */
export type IngestQueryLine = {
  clientKey: string;
  label: string;
  query: string;
  enabled: boolean;
};
