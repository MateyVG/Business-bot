-- Secure-public: забранява четенето с anon ключа.
-- Така репото може да е ПУБЛИЧНО без да изтичат данни — публичният anon ключ
-- става безполезен, а приложението чете със service ключа (само в secrets).
-- service_role заобикаля RLS, затова четенето в приложението продължава да работи.
--
-- Изпълни в Supabase -> SQL Editor -> Run.

drop policy if exists "anon read sales"   on sales;
drop policy if exists "anon read costs"   on product_costs;
drop policy if exists "anon read weather" on weather;

-- RLS остава включен; без политики anon няма достъп, service_role има пълен.
alter table sales         enable row level security;
alter table product_costs enable row level security;
alter table weather       enable row level security;
