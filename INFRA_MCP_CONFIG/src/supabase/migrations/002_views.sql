-- ============================================================
-- 002_views.sql
-- Vistas analíticas para dashboards y agente CSM
-- ============================================================

-- Vista: últimos health scores por cuenta (1 fila por deal)
create or replace view v_latest_health as
select distinct on (pipedrive_deal_id)
  pipedrive_deal_id,
  score,
  risk_level,
  engagement_rate,
  last_login,
  nrr,
  recorded_at
from account_health
order by pipedrive_deal_id, recorded_at desc;

-- Vista: cuentas críticas activas
create or replace view v_churn_radar as
select
  pipedrive_deal_id,
  score,
  risk_level,
  engagement_rate,
  last_login,
  nrr,
  recorded_at,
  case
    when score < 30                          then 'CRITICAL — acción inmediata'
    when score between 30 and 49             then 'HIGH — revisar esta semana'
    when score between 50 and 69             then 'MEDIUM — monitorear'
    else                                          'LOW — ok'
  end as action_label,
  extract(days from now() - last_login)::int as days_since_login
from v_latest_health
where risk_level in ('high', 'critical')
order by score asc;

-- Vista: resumen del pipeline de renovaciones
create or replace view v_renewal_summary as
select
  risk_level,
  count(*)                                  as accounts,
  round(avg(score), 1)                      as avg_score,
  round(avg(nrr), 2)                        as avg_nrr,
  round(avg(engagement_rate), 2)            as avg_engagement
from v_latest_health
group by risk_level
order by
  case risk_level
    when 'critical' then 1
    when 'high'     then 2
    when 'medium'   then 3
    when 'low'      then 4
  end;

-- Vista: funnel de leads de agencia
create or replace view v_agency_funnel as
select
  status,
  count(*)                                  as leads,
  round(avg(diagnostic_score), 1)           as avg_score,
  min(created_at)                           as first_lead,
  max(created_at)                           as last_lead
from agency_leads
group by status
order by
  case status
    when 'new'      then 1
    when 'contacted'then 2
    when 'qualified'then 3
    when 'proposal' then 4
    when 'won'      then 5
    when 'lost'     then 6
  end;
