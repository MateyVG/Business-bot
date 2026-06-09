-- Миграция: product_costs става "по канал" (на място / доставка), свързване по ИМЕ.
-- Причина: Excel-ът със себестойностите няма Мат. №, а само име на артикул, и
-- дава различна себестойност за обектите и за доставките.
--
-- Изпълни в Supabase -> SQL Editor -> New query.
-- ВНИМАНИЕ: трие старата таблица product_costs (тя беше празна/с друг ключ).

drop table if exists product_costs cascade;

create table product_costs (
    product_name  text not null,        -- връзка към sales.product_name
    channel       text not null,        -- 'onsite' (на място) | 'delivery' (доставка)
    unit_cost     numeric,              -- себестойност за единица (с ДДС)
    updated_at    timestamptz default now(),
    primary key (product_name, channel)
);

-- RLS: четене с anon ключа (политиката беше премахната с drop ... cascade)
alter table product_costs enable row level security;
create policy "anon read costs" on product_costs for select using (true);
