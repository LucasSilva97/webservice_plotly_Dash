-- Grão: revenda x mês x canal ('IMEDIATO', 'ABASTECIMENTO' e 'TODOS', que junta os dois).
-- Painel do fabricante do programa (var fabricante_programa): caixas e clientes com compra contam
-- só os produtos dele; 'TODOS' conta uma vez o cliente que comprou nos dois canais.
-- clientes_acumulados_ano = clientes distintos com compra de janeiro até o mês (total do ano).
-- A ruptura é a da carteira inteira da revenda e não muda com o canal.
with vendas as (
    select v.revenda_id, v.mes, v.cliente_id, p.canal, v.caixas_liquidas
    from {{ ref('int_vendas_dia') }} as v
    inner join {{ ref('int_produtos_analise') }} as p on p.produto_id = v.produto_id
    where p.fabricante = '{{ var("fabricante_programa") }}'
),

por_cliente as (
    select revenda_id, mes, canal, cliente_id, sum(caixas_liquidas) as caixas
    from vendas
    group by revenda_id, mes, canal, cliente_id
    union all
    select revenda_id, mes, 'TODOS', cliente_id, sum(caixas_liquidas)
    from vendas
    group by revenda_id, mes, cliente_id
),

mensal as (
    select revenda_id, mes, canal,
           sum(caixas) as caixas_fabricante,
           count(*) filter (where caixas > 0) as clientes_com_compra
    from por_cliente
    group by revenda_id, mes, canal
),

acumulado as (
    select a.revenda_id, a.mes, a.canal, count(distinct b.cliente_id) as clientes_acumulados_ano
    from mensal as a
    inner join por_cliente as b
        on b.revenda_id = a.revenda_id
       and b.canal = a.canal
       and b.mes between (a.mes // 100) * 100 + 1 and a.mes
       and b.caixas > 0
    group by a.revenda_id, a.mes, a.canal
),

espinha as (
    select r.revenda_id, c.mes, k.canal
    from {{ ref('stg_revendas') }} as r
    cross join (select distinct mes from {{ ref('int_calendario') }}) as c
    cross join (values ('IMEDIATO'), ('ABASTECIMENTO'), ('TODOS')) as k(canal)
),

metas as (
    select * from {{ ref('int_metas') }} where vendedor_id = 0
),

ruptura as (
    select revenda_id, mes,
           round(100.0 * sum(clientes_sem_compra) / nullif(sum(clientes_ativos), 0), 2) as perc_ruptura
    from {{ ref('ruptura_vendedor_mes') }}
    group by revenda_id, mes
)

select
    e.revenda_id,
    e.mes,
    e.mes // 100 as ano,
    e.mes % 100 as mes_calendario,
    e.canal,
    m.caixas_fabricante,
    m.clientes_com_compra,
    a.clientes_acumulados_ano,
    case e.canal
        when 'IMEDIATO' then mt.meta_caixas_fabricante_imediato
        when 'ABASTECIMENTO' then mt.meta_caixas_fabricante_abastecimento
        else mt.meta_caixas_fabricante_imediato + mt.meta_caixas_fabricante_abastecimento
    end as meta_caixas,
    mt.meta_clientes_positivados as meta_clientes,
    rp.perc_ruptura,
    s.meta_ruptura_pct as meta_ruptura
from espinha as e
left join mensal as m on m.revenda_id = e.revenda_id and m.mes = e.mes and m.canal = e.canal
left join acumulado as a on a.revenda_id = e.revenda_id and a.mes = e.mes and a.canal = e.canal
left join metas as mt on mt.revenda_id = e.revenda_id and mt.mes = e.mes
left join ruptura as rp on rp.revenda_id = e.revenda_id and rp.mes = e.mes
left join {{ ref('metas_ruptura_fabricante') }} as s on s.mes_calendario = e.mes % 100
