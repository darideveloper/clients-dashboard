erDiagram
    %% Source: ourlives/models.py + sales ingestion spec (Formidable Ourlens US Order Form V2). Django entities are source of truth. Keeps full 14-table aspirational CRM.
    %% === Implemented — Django models.py ===
    projects {
        int project_id PK "e.g. 1, Django Project model"
        string name UK "e.g. ourlens, ourplan required, Project.name"
        string description "e.g. App project, Project.description"
    }

    organizations {
        int organization_id PK "e.g. 12 ex-companies, Django Organization model"
        string name UK "e.g. Acme Health Ltd required, Organization.name"
        string description "e.g. Billing entity, Organization.description"
        int assigned_rep_id FK "e.g. 7->John nullable, ERD companies.assigned_rep_id"
        date first_order_date "e.g. 2026-01-15 derived"
        date last_order_date "e.g. 2026-09-02 derived"
        int total_orders "e.g. 3 derived"
        decimal total_revenue "e.g. 12500.00 derived"
    }

    invitation_codes {
        int invitation_code_id PK "e.g. 501 ex-codes.code_id, InvitationCode.id"
        int project_id FK "e.g. 1->ourlens required, FK->projects PROTECT"
        int organization_id FK "e.g. 12->Acme required, FK->organizations PROTECT"
        string code UK "e.g. ACME-LONDON-001 required, code_value field_od22f2, InvitationCode.code"
        boolean is_active "e.g. true required, InvitationCode.is_active"
        int max_use "e.g. 5 required independent of code_type, InvitationCode.max_use"
        int current_use "e.g. 2 CHECK current_use<=max_use, InvitationCode.current_use"
        int order_id FK "e.g. 82->OL-82 nullable PROTECT, FK->orders, new additive"
        int code_type_id FK "e.g. 1->Up to 5 nullable PROTECT, FK->code_types, new additive"
        int sequence "e.g. 1 nullable 1-20 no DB constraint"
    }

    app_settings {
        int app_settings_id PK "e.g. 1 Singleton, AppSettings model"
        int total_tokens "e.g. 100 required, AppSettings.total_tokens"
        decimal price_per_token "e.g. 0.10 USD, AppSettings.price_per_token"
        decimal min_purchase_amount "e.g. 5.00 USD, AppSettings.min_purchase_amount"
        string stripe_product_id "e.g. prod_xxx nullable, AppSettings.stripe_product_id"
        string stripe_price_id "e.g. price_xxx nullable, AppSettings.stripe_price_id"
        string storage_base_url "e.g. https://storage.example nullable, AppSettings.storage_base_url"
        int tokens_assigned "e.g. 20 derived SUM invitation_codes.max_use"
        int tokens_used "e.g. 6 derived SUM invitation_codes.current_use"
        int tokens_available "e.g. 80 derived total_tokens-assigned"
    }

    stripe_events {
        int id PK "e.g. 1, Django StripeEvent.id (auto)"
        string stripe_event_id UK "e.g. evt_test_123 UK, StripeEvent.stripe_event_id"
        string source "e.g. ourlives required, StripeEvent.source"
        int token_count "e.g. 50 required, StripeEvent.token_count"
        int amount_cents "e.g. 1000 required, StripeEvent.amount_cents"
        string presentment_currency "e.g. eur nullable, StripeEvent.presentment_currency"
        int presentment_amount "e.g. 920 nullable, StripeEvent.presentment_amount"
        datetime handled_at "e.g. 2026-09-02T01:45:00Z, StripeEvent.handled_at"
    }

    %% === Planned — aspirational CRM (countries/currencies/products etc.) ===
    countries {
        int country_id PK "e.g. 1"
        string iso2 UK "e.g. US, GB, CA required, from field_enrcy2_country"
        string iso3 UK "e.g. USA, GBR required"
        string name UK "e.g. United States required, 250 options"
        string region "e.g. NA, EU nullable"
        boolean active "e.g. true required"
    }

    currencies {
        int currency_id PK "e.g. 1"
        string code UK "e.g. USD required, field_mo8wu/field_5znvs"
        string name "e.g. US Dollar required"
        string symbol_left "e.g. $ required"
        string symbol_right "e.g.  empty"
        decimal exchange_rate "e.g. 1.00, 1.35 CAD"
        int country_id FK "e.g. 1->USA nullable, FK->countries"
        boolean active "e.g. true required"
    }

    products {
        int product_id PK "e.g. 1 distinct from projects, field_q8zvr2"
        int currency_id FK "e.g. 1->USD required"
        string name "e.g. Micro Pilot required, field_q8zvr2"
        string tier "e.g. micro required, ENUM regional/enterprise"
        decimal unit_price "e.g. 995.00 required, data-frmprice"
        boolean active "e.g. true required"
        string description "e.g. Pilot bundle 500 tokens"
    }

    code_types {
        int code_type_id PK "e.g. 1"
        string code UK "e.g. up_to_5 required"
        string name "e.g. Up to 5 Additional Codes required, field_uwfjk2"
        int max_codes "e.g. 5 required independent of invitation_codes.max_use"
        boolean active "e.g. true required"
        string description "e.g. Small team bundle, separate frontend field"
    }

    reps {
        int rep_id PK "e.g. 7"
        string first_name "e.g. John required, field_9ayr32_first"
        string last_name "e.g. Doe required, field_9ayr32_last"
        string email UK "e.g. john@ourlivesapp.com required unique, field_s7sd2"
        int total_orders "e.g. 12 derived"
        decimal total_revenue "e.g. 45600.00 derived SUM"
    }

    organization_addresses {
        int address_id PK "e.g. 101 ex-company_addresses"
        int organization_id FK "e.g. 12->Acme required, FK->organizations"
        string line1 "e.g. 10 Downing St required, field_enrcy2_line1"
        string line2 "e.g. Suite 2 nullable, field_enrcy2_line2"
        string city "e.g. London required, field_enrcy2_city"
        string state "e.g. Greater London required, field_enrcy2_state"
        string zip "e.g. SW1A 2AA required, field_enrcy2_zip"
        int country_id FK "e.g. 826->UK required, FK->countries field_enrcy2_country"
        boolean is_primary "e.g. true required"
    }

    contact_types {
        int contact_type_id PK "e.g. 1"
        string code UK "primary, invoice, billing, technical"
        string name "Primary Contact, Invoice Contact, Billing"
        boolean active "true = selectable in form"
        string description "Extensible contact role, from 616/619"
    }

    contacts {
        int contact_id PK "e.g. 31"
        int organization_id FK "e.g. 12 -> Acme Ltd, required, ex-company_id"
        int contact_type_id FK "FK->contact_types, e.g. 1=Primary"
        string first_name "e.g. Alice, required"
        string last_name "e.g. Smith, required"
        string email "e.g. alice@acme.com, required valid email"
        string phone "e.g. +44 7700 900123 tel, required"
    }

    order_types {
        int order_type_id PK "e.g. 1=Pilot, 2=Standard, 3=Trial"
        string code UK "pilot, standard, trial, renewal"
        string name "Pilot Order, Standard Order, Trial Order"
        boolean active "true = show as radio option in frmrules"
        string description "Extensible order type, replaces hard boolean"
    }

    orders {
        int order_id PK "e.g. 82"
        string order_number UK "OL - 82 readonly, required, from field_be8ml"
        int organization_id FK "e.g. 12 Acme Ltd, required, ex-company_id"
        int rep_id FK "e.g. 7 John Doe, required"
        int primary_contact_id FK "e.g. 31 Alice Smith, required"
        int invoice_contact_id FK "e.g. 32 Bob Smith, required"
        int currency_id FK "nullable, for non-pilot e.g. 1=USD, field_mo8wu"
        int pilot_currency_id FK "nullable, for pilot e.g. 3=GBP field_5znvs"
        boolean is_pilot_order "e.g. true->Pilot @property from M2M code=pilot, no column"
        boolean is_upgrade_from_pilot "nullable, e.g. true→show 613 banner, field_r9jxe2"
        boolean is_referral_order "e.g. true, field_53psq2"
        string referral_organisation "nullable, e.g. NHS Trust Midlands, field_t6li52"
        string po_number "e.g. PO-2026-8842, field_c8rim2 required"
        int number_of_scans "nullable, e.g. 500, field_mey192"
        decimal cost_per_scan "nullable, e.g. 2.50, field_8id4t"
        decimal total_agreed_price "@property: number_of_scans*cost_per_scan, e.g. 1250.00, no column"
        string additional_information "e.g. Need invoice by month end, textarea field_684"
        string ip_address "e.g. 203.0.113.45 system"
        string form_entry_key "e.g. kR3x9 Formidable key"
        datetime submitted_at "e.g. 2026-09-02T01:45:00Z"
        boolean hcaptcha_verified "e.g. true"
    }

    order_order_types {
        int order_id PK, FK "e.g. 82, PK composite"
        int order_type_id PK, FK "e.g. 1=Pilot + 3=Referral, PK composite"
        string notes "e.g. junction for upgrades/referrals many-to-many, frmrules driven"
    }

    order_items {
        int order_item_id PK "e.g. 201"
        int order_id FK "e.g. 82->OL-82 required"
        int product_id FK "e.g. 2->Regional Pilot required"
        int quantity "e.g. 2 required, field_alh5s2"
        decimal unit_price "e.g. 3995.00 required snapshot data-frmprice"
        decimal line_total "@property: quantity*unit_price, e.g. 7990.00, no column"
    }

    %% Relationships
    countries ||--o{ organization_addresses : "has"
    countries ||--o{ currencies : "has"
    currencies ||--o{ products : "has"
    currencies ||--o{ orders : "currency_for_non_pilot"
    currencies ||--o{ orders : "pilot_currency"

    organizations ||--o{ organization_addresses : "has"
    organizations ||--o{ contacts : "has"
    organizations ||--o{ orders : "places"
    organizations ||--o{ invitation_codes : "owns"

    projects ||--o{ invitation_codes : "defines"

    reps ||--o{ organizations : "assigned_to"
    reps ||--o{ orders : "owns"

    contact_types ||--o{ contacts : "categorizes"
    contacts ||--o{ orders : "primary_for"
    contacts ||--o{ orders : "invoice_for"

    order_types ||--o{ order_order_types : "categorizes"
    orders ||--o{ order_order_types : "has_junction"
    orders ||--o{ order_items : "contains"
    products ||--o{ order_items : "ordered_as"

    orders ||--o{ invitation_codes : "has"
    code_types ||--o{ invitation_codes : "categorizes"
