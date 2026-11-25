-- Grão: mês. Dias úteis do mês e dias úteis decorridos até a data de referência
-- (base da tendência: realizado / dias decorridos x dias do mês).
select
    mes,
    min(data) as inicio,
    max(data) as fim,
    count(*) filter (where dia_util) as dias_uteis_mes,
    count(*) filter (where dia_util and data <= {{ data_referencia() }}) as dias_uteis_decorridos,
    {{ data_referencia() }} as data_referencia,
    mes = {{ mes_int(data_referencia()) }} as mes_atual
from {{ ref('int_calendario') }}
group by mes
