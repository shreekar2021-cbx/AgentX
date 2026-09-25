-- Add farmer-entered budget and lab-measured micronutrients without changing
-- existing farm or soil-test rows. Keep the micronutrient shape bounded in DB too.

begin;

alter table public.farms
  add column budget_inr numeric(14, 2),
  add constraint farms_budget_inr_nonnegative
    check (budget_inr is null or budget_inr >= 0);

create or replace function public.valid_micronutrients_mg_kg(payload jsonb)
returns boolean
language plpgsql
immutable
strict
set search_path = pg_catalog, public
as $$
declare
  item record;
  amount numeric;
begin
  if jsonb_typeof(payload) <> 'object' then
    return false;
  end if;

  for item in select key, value from jsonb_each(payload) loop
    if item.key not in (
      'iron', 'zinc', 'manganese', 'copper', 'boron', 'molybdenum', 'chloride'
    ) or jsonb_typeof(item.value) <> 'number' then
      return false;
    end if;
    amount := (item.value #>> '{}')::numeric;
    if amount < 0 or amount > 10000 or amount <> trunc(amount, 3) then
      return false;
    end if;
  end loop;

  return true;
exception when others then
  return false;
end;
$$;

-- The table constraint calls this function for user and service-role writes.
revoke all on function public.valid_micronutrients_mg_kg(jsonb) from public, anon;
grant execute on function public.valid_micronutrients_mg_kg(jsonb) to authenticated, service_role;

alter table public.soil_tests
  add column micronutrients_mg_kg jsonb not null default '{}'::jsonb,
  add constraint soil_tests_micronutrients_valid
    check (public.valid_micronutrients_mg_kg(micronutrients_mg_kg));

-- Existing table grants are column-scoped, so explicitly allow these fields.
grant insert (budget_inr), update (budget_inr)
  on public.farms to authenticated;
grant insert (micronutrients_mg_kg)
  on public.soil_tests to authenticated;

commit;
