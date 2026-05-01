-- ============================================================
-- 001_initial_schema.sql
-- Tablas base del Agente CSM Maestro
-- Ejecutar en Supabase SQL Editor o via CLI: supabase db push
-- ============================================================

-- ----------------------------------------------------------------
-- account_health — historial de health scores por cuenta
-- ----------------------------------------------------------------
create table if not exists account_health (
  id                uuid primary key default gen_random_uuid(),
  pipedrive_deal_id bigint not null,
  score             smallint not null check (score between 0 and 100),
  risk_level        text not null check (risk_level in ('low', 'medium', 'high', 'critical')),
  engagement_rate   numeric(5,2),
  last_login        timestamptz,
  nrr               numeric(6,2),
  notes             text,
  recorded_at       timestamptz not null default now()
);

create index if not exists idx_account_health_deal on account_health (pipedrive_deal_id);
create index if not exists idx_account_health_risk on account_health (risk_level, recorded_at desc);

-- ----------------------------------------------------------------
-- csm_interactions — registro de interacciones del CSM
-- ----------------------------------------------------------------
create table if not exists csm_interactions (
  id           uuid primary key default gen_random_uuid(),
  deal_id      bigint not null,
  type         text not null check (type in ('call', 'email', 'qbr', 'whatsapp', 'note', 'renewal', 'churn_risk')),
  summary      text not null,
  outcome      text,
  next_action  text,
  next_date    date,
  created_at   timestamptz not null default now()
);

create index if not exists idx_interactions_deal on csm_interactions (deal_id, created_at desc);
create index if not exists idx_interactions_type on csm_interactions (type, created_at desc);

-- ----------------------------------------------------------------
-- agency_leads — leads capturados por la agencia
-- ----------------------------------------------------------------
create table if not exists agency_leads (
  id               uuid primary key default gen_random_uuid(),
  name             text not null,
  email            text not null,
  company          text,
  diagnostic_score smallint check (diagnostic_score between 0 and 100),
  source           text default 'diagnostico_express',
  status           text not null default 'new'
                   check (status in ('new', 'contacted', 'qualified', 'proposal', 'won', 'lost')),
  notes            text,
  created_at       timestamptz not null default now()
);

create index if not exists idx_leads_status on agency_leads (status, created_at desc);
create index if not exists idx_leads_email on agency_leads (email);

-- ----------------------------------------------------------------
-- content_metrics — métricas de contenido (marca personal)
-- ----------------------------------------------------------------
create table if not exists content_metrics (
  id               uuid primary key default gen_random_uuid(),
  platform         text not null check (platform in ('linkedin', 'instagram', 'email', 'youtube')),
  post_url         text,
  title            text,
  impressions      integer default 0,
  engagement_rate  numeric(5,2) default 0,
  leads_generated  integer default 0,
  published_at     timestamptz not null
);

create index if not exists idx_content_platform on content_metrics (platform, published_at desc);

-- ----------------------------------------------------------------
-- agency_payments — pagos y servicios de la agencia
-- ----------------------------------------------------------------
create table if not exists agency_payments (
  id                uuid primary key default gen_random_uuid(),
  lead_id           uuid references agency_leads (id) on delete set null,
  service           text not null,
  amount            numeric(10,2) not null,
  currency          text not null default 'USD',
  status            text not null default 'pending'
                    check (status in ('pending', 'paid', 'failed', 'refunded')),
  stripe_payment_id text unique,
  created_at        timestamptz not null default now()
);

create index if not exists idx_payments_status on agency_payments (status, created_at desc);
create index if not exists idx_payments_lead on agency_payments (lead_id);

-- ----------------------------------------------------------------
-- Row Level Security — habilitar en todas las tablas
-- ----------------------------------------------------------------
alter table account_health    enable row level security;
alter table csm_interactions  enable row level security;
alter table agency_leads      enable row level security;
alter table content_metrics   enable row level security;
alter table agency_payments   enable row level security;

-- Política: solo service_role puede leer/escribir (acceso desde n8n y Claude)
create policy "service_role full access" on account_health
  using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

create policy "service_role full access" on csm_interactions
  using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

create policy "service_role full access" on agency_leads
  using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

create policy "service_role full access" on content_metrics
  using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

create policy "service_role full access" on agency_payments
  using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
