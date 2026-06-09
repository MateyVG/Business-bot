-- Схема за Supabase. Изпълни в: SQL Editor -> New query.

-- ===== Продажби (ниво артикул) =====
create table if not exists sales (
    id              bigint generated always as identity primary key,
    object_name     text,            -- обект/заведение
    order_no        bigint,          -- номер на бон/поръчка
    sold_at         timestamptz,     -- точен час на продажбата
    business_date   date,            -- РАБОТЕН ден (граница 07:00)
    sale_hour       smallint,        -- час на продажбата (за анализ по часове)
    operator        text,            -- касиер
    material_id     bigint,          -- Мат. №
    product_name    text,
    quantity        numeric,
    unit            text,
    receipt         integer,
    partner         text,            -- партньор (напр. Online Orders); NULL = на място
    is_delivery     boolean,         -- доставка по домовете (partner е попълнен)
    is_return       boolean,         -- връщане (отрицателна стойност)
    contact_person  text,
    category        text,
    doc_no          bigint,
    amount          numeric,         -- стойност (приход)
    created_at      timestamptz default now()
);

create index if not exists idx_sales_bdate    on sales (business_date);
create index if not exists idx_sales_object   on sales (object_name);
create index if not exists idx_sales_category on sales (category);
create index if not exists idx_sales_delivery on sales (is_delivery);

-- ===== Себестойности на продуктите (по канал) =====
-- Себестойността на един и същ продукт се различава на място vs доставка,
-- затова ключът е (product_name, channel). Връзката към sales е по име.
create table if not exists product_costs (
    product_name  text not null,        -- връзка към sales.product_name
    channel       text not null,        -- 'onsite' (на място) | 'delivery' (доставка)
    unit_cost     numeric,              -- себестойност за единица (с ДДС)
    updated_at    timestamptz default now(),
    primary key (product_name, channel)
);

-- ===== Синоптични данни (за корелация време <-> оборот) =====
create table if not exists weather (
    city            text,
    day             date,
    temp_max        numeric,
    temp_min        numeric,
    precipitation   numeric,   -- мм валежи
    weather_code    integer,   -- WMO код (ясно/дъжд/сняг...)
    primary key (city, day)
);

-- ===== RLS: разрешаваме четене с anon ключа =====
alter table sales         enable row level security;
alter table product_costs enable row level security;
alter table weather       enable row level security;

create policy "anon read sales"   on sales         for select using (true);
create policy "anon read costs"   on product_costs for select using (true);
create policy "anon read weather" on weather        for select using (true);
