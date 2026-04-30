-- TikTok Automation — Script Queue Schema
-- รันใน Supabase SQL Editor

create table if not exists video_scripts (
  id              bigserial primary key,
  title           text not null,
  category        text default '',
  scene1_prompt   text not null,
  scene2_prompt   text not null,

  status          text not null default 'pending',
                  -- pending | processing | done | failed

  publish_id      text,
  video_path      text,
  cost_usd        numeric(10, 4),
  error           text,

  created_at      timestamptz not null default now(),
  started_at      timestamptz,
  completed_at    timestamptz
);

create index if not exists idx_video_scripts_status_created
  on video_scripts (status, created_at);

-- View: queue stats
create or replace view video_scripts_stats as
select
  status,
  count(*)              as total,
  sum(cost_usd)         as cost_usd,
  min(created_at)       as oldest,
  max(completed_at)     as latest_done
from video_scripts
group by status;

-- View: คลิป 7 วันล่าสุด
create or replace view video_scripts_recent as
select id, title, status, publish_id, cost_usd, completed_at
from video_scripts
where completed_at >= now() - interval '7 days'
order by completed_at desc nulls last;
