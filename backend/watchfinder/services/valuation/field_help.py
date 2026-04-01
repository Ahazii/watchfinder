"""Short guidance strings for listing detail editable fields."""

FIELD_GUIDANCE: dict[str, str] = {
    "model_family": "Model line or family (e.g. Seamaster 300, Speedmaster). Used with brand to match internal sale comps. Overrides parsed title hints when you set it manually.",
    "reference": "Case or model reference if you know it (e.g. 165.024). Tightens comps when sale records include references.",
    "caliber": "Movement calibre (e.g. cal 565, ETA 2824). Source letter shows whether you typed it (M), we parsed it (R), or you used search/AI later (S/I).",
    "repair_supplement": "Extra repair/parts cost on top of the automatic rule-based estimate — e.g. known overhaul, parts you already bought, or a historical average you trust.",
    "donor_cost": "Expected cost to buy a donor movement or parts lot (eBay search or manual). Included in total repair for profit math.",
    "recorded_sale": "If this listing ended and you know the hammer/sale price, record it here. It feeds your private comp database (not eBay history API).",
    "notes": "Freeform notes — work plan, risks, links, anything you want saved with the listing.",
    "comps": "Bands use only data inside this app: recorded sales you entered, or asking prices of other active listings with the same parsed brand.",
}
