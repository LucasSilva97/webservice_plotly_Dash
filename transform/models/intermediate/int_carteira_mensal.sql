-- Grão: revenda x mês x cliente. A carteira "na competência": quem estava cadastrado no mês,
-- com o vendedor vigente no fechamento (ou na data de referência, no mês corrente).
-- O cliente bloqueado aparece até o mês do bloqueio, com ativo_no_fechamento = false.
with meses as (
    select
        mes,
        min(data) as inicio,
        least(max(data), {{ data_referencia() }}) as fechamento
    from {{ ref('int_calendario') }}
    where data <= {{ data_referencia() }}
    group by mes
),

vigencia as (
    select
        cliente_id,
        vendedor_id,
        vigente_desde,
        lead(vigente_desde) over (partition by cliente_id order by vigente_desde) as vigente_ate
    from {{ ref('stg_clientes_vendedor_hist') }}
)

select
    c.revenda_id,
    m.mes,
    c.cliente_id,
    v.vendedor_id,
    c.data_cadastro between m.inicio and m.fechamento as novo_no_mes,
    coalesce(c.data_bloqueio between m.inicio and m.fechamento, false) as bloqueado_no_mes,
    c.data_bloqueio is null or c.data_bloqueio > m.fechamento as ativo_no_fechamento
from {{ ref('stg_clientes') }} as c
inner join meses as m
    on c.data_cadastro <= m.fechamento
   and (c.data_bloqueio is null or c.data_bloqueio >= m.inicio)
inner join vigencia as v
    on v.cliente_id = c.cliente_id
   and v.vigente_desde <= m.fechamento
   and (v.vigente_ate is null or v.vigente_ate > m.fechamento)
