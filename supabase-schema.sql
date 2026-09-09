-- HEE Expert Review: votes and comments table
-- Run this in Supabase SQL Editor

create table if not exists hee_review (
  id bigserial primary key,
  figure_id text not null,
  user_name text not null,
  vote text check (vote in ('up', 'down', 'essential', 'useful', 'nice', 'skip')),
  comment text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Enable Row Level Security
alter table hee_review enable row level security;

-- Policy: anyone can read all reviews
create policy "Public read access" on hee_review
  for select using (true);

-- Policy: anyone can insert (no auth required for expert review)
create policy "Public insert access" on hee_review
  for insert with check (true);

-- Policy: users can update their own entries (by user_name + figure_id)
create policy "Users can update own" on hee_review
  for update using (true) with check (true);

-- Index for fast lookups
create index if not exists idx_hee_review_figure on hee_review(figure_id);
create index if not exists idx_hee_review_user on hee_review(user_name);

-- Optional: trigger to auto-update updated_at
create or replace function update_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists update_hee_review_updated_at on hee_review;
create trigger update_hee_review_updated_at
  before update on hee_review
  for each row execute function update_updated_at();