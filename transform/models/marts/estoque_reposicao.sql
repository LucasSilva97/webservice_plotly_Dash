-- Grão: revenda x produto x período x base de estoque.
--   período: MES_ATUAL (dia 1 até a data de referência), MES_ANTERIOR, ULTIMOS_30_DIAS
--   base:    SISTEMA (saldo do ERP) ou CONTAGEM (última contagem física; sem contagem, o saldo do ERP)
-- Regra (parâmetros em dbt_project.yml): média diária = volume líquido do período / dias úteis;
-- mínimo = média x dias_estoque_minimo; máximo = média x dias_estoque_maximo. Abaixo do mínimo,
-- puxar até o mínimo (positivo); acima do máximo, reduzir até o máximo (negativo); na faixa, zero.
-- Produto sem custo vigente fica fora (não dá para valorizar a reposição).
with periodos as (
    select 'MES_ATUAL' as periodo,
           cast(date_trunc('month', {{ data_referencia() }}) as date) as inicio,
           {{ data_referencia() }} as fim
    union all
    select 'MES_ANTERIOR',
           cast(date_trunc('month', {{ data_referencia() }}) - interval 1 month as date),
           cast(date_trunc('month', {{ data_referencia() }}) as date) - 1
    union all
    select 'ULTIMOS_30_DIAS', {{ data_referencia() }} - 29, {{ data_referencia() }}
),

dias_uteis as (
    select p.periodo, count(*) filter (where c.dia_util) as dias_uteis
    from periodos as p
    inner join {{ ref('int_calendario') }} as c on c.data between p.inicio and p.fim
    group by p.periodo
),

vendas as (
    select v.revenda_id, v.produto_id, p.periodo,
           sum(v.caixas_liquidas) as qtd_vendida,
           sum(v.valor_liquido) as valor_vendido
    from {{ ref('int_vendas_dia') }} as v
    inner join periodos as p on v.data between p.inicio and p.fim
    group by v.revenda_id, v.produto_id, p.periodo
),

contagem as (
    select revenda_id, produto_id, data_contagem, qtd_contada
    from {{ ref('stg_contagens_estoque') }}
    qualify row_number() over (partition by revenda_id, produto_id order by data_contagem desc) = 1
),

bases as (
    select s.revenda_id, s.produto_id, 'SISTEMA' as base_estoque, s.saldo_caixas as saldo
    from {{ ref('stg_estoque_saldos') }} as s
    union all
    select s.revenda_id, s.produto_id, 'CONTAGEM', coalesce(c.qtd_contada, s.saldo_caixas)
    from {{ ref('stg_estoque_saldos') }} as s
    left join contagem as c on c.revenda_id = s.revenda_id and c.produto_id = s.produto_id
),

transito as (
    select revenda_id, produto_id, sum(qtd_caixas) as qtd_transito
    from {{ ref('int_transito') }}
    group by revenda_id, produto_id
),

base as (
    select
        r.revenda_id, r.revenda, p.produto_id, p.produto, p.marca, p.fabricante, p.categoria, p.canal,
        p.litros_por_caixa, per.periodo, per.inicio, per.fim, b.base_estoque, b.saldo,
        cont.data_contagem, cv.custo_caixa, du.dias_uteis,
        coalesce(v.qtd_vendida, 0) as qtd_vendida,
        coalesce(v.valor_vendido, 0) as valor_vendido,
        coalesce(t.qtd_transito, 0) as qtd_transito,
        uc.ultima_compra,
        round(coalesce(v.qtd_vendida, 0) / nullif(du.dias_uteis, 0), 4) as media_venda_dia
    from bases as b
    inner join {{ ref('stg_revendas') }} as r on r.revenda_id = b.revenda_id
    inner join {{ ref('int_produtos_analise') }} as p on p.produto_id = b.produto_id
    inner join {{ ref('int_custo_vigente') }} as cv on cv.revenda_id = b.revenda_id and cv.produto_id = b.produto_id
    cross join periodos as per
    inner join dias_uteis as du on du.periodo = per.periodo
    left join vendas as v on v.revenda_id = b.revenda_id and v.produto_id = b.produto_id and v.periodo = per.periodo
    left join transito as t on t.revenda_id = b.revenda_id and t.produto_id = b.produto_id
    left join {{ ref('int_ultima_compra') }} as uc on uc.revenda_id = b.revenda_id and uc.produto_id = b.produto_id
    left join contagem as cont on cont.revenda_id = b.revenda_id and cont.produto_id = b.produto_id
),

faixa as (
    -- Em caixas inteiras, arredondando para cima.
    select
        *,
        cast(ceil(media_venda_dia * {{ var('dias_estoque_minimo') }}) as integer) as estoque_minimo,
        cast(ceil(media_venda_dia * {{ var('dias_estoque_maximo') }}) as integer) as estoque_maximo
    from base
),

reposicao as (
    select
        *,
        case
            when saldo < estoque_minimo then estoque_minimo - saldo
            when saldo > estoque_maximo then estoque_maximo - saldo
            else 0
        end as reduzir_puxar
    from faixa
)

select
    revenda_id, revenda, produto_id, produto, marca, fabricante, categoria, canal,
    periodo,
    {{ mes_int('inicio') }} as mes_inicio,
    {{ mes_int('fim') }} as mes_fim,
    base_estoque,
    saldo as saldo_caixas,
    data_contagem,
    custo_caixa,
    litros_por_caixa,
    round(saldo * litros_por_caixa / 100, 2) as hl_estoque,
    qtd_vendida,
    round(valor_vendido, 2) as valor_vendido,
    dias_uteis,
    media_venda_dia,
    round(media_venda_dia * litros_por_caixa / 100, 4) as media_hl_dia,
    estoque_minimo,
    estoque_maximo,
    reduzir_puxar,
    round(reduzir_puxar * custo_caixa, 2) as analise_rs,
    greatest(estoque_maximo - saldo, 0) as puxada_maxima,
    round(saldo * custo_caixa, 2) as estoque_valorizado,
    round(saldo / nullif(media_venda_dia, 0), 1) as dde,
    qtd_transito,
    round((saldo + qtd_transito) / nullif(media_venda_dia, 0), 1) as dde_com_transito,
    saldo = 0 and media_venda_dia > 0 as em_ruptura,
    ultima_compra,
    date_diff('day', ultima_compra, {{ data_referencia() }}) as dias_desde_ultima_compra,
    coalesce(date_diff('day', ultima_compra, {{ data_referencia() }}) > {{ var('dias_compra_antiga') }}, false) as compra_antiga
from reposicao
