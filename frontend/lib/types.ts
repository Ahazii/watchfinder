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
  score?: OpportunityScore | null;
};

export type ParsedAttribute = { key: string; value_text: string | null };
export type RepairSignal = {
  signal_type: string;
  matched_text: string | null;
  source_field: string | null;
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
  ingest_queries: IngestQueryDto[];
  env_fallback_query: string;
};

/** Client-only row key + editable fields */
export type IngestQueryLine = {
  clientKey: string;
  label: string;
  query: string;
  enabled: boolean;
};
