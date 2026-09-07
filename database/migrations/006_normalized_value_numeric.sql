-- Phase 05: Fact Normalization & Context
-- Add normalized_value_numeric to public.facts to support standard mathematical comparison
-- across heterogeneous numerical scales (Crore, Lakh, Million, Billion).

alter table public.facts
add column if not exists normalized_value_numeric double precision;
