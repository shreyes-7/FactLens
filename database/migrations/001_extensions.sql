-- Required PostgreSQL extensions for UUID generation and vector storage.
create extension if not exists pgcrypto;
create extension if not exists vector;
