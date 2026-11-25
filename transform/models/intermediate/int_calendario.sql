-- Grão: dia. Do início do ano anterior ao fim do ano da data de referência.
-- Dia útil = segunda a sexta, menos os feriados do seed.
with dias as (
    select cast(generate_series as date) as data
    from generate_series(
        cast(date_trunc('year', {{ data_referencia() }}) - interval 1 year as timestamp),
        cast(date_trunc('year', {{ data_referencia() }}) + interval 1 year - interval 1 day as timestamp),
        interval 1 day
    )
)
select
    d.data,
    {{ mes_int('d.data') }} as mes,
    isodow(d.data) as dia_semana,
    f.data is not null as feriado,
    isodow(d.data) <= 5 and f.data is null as dia_util
from dias as d
left join {{ ref('feriados') }} as f on f.data = d.data
