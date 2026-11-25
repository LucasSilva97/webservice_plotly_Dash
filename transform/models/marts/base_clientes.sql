-- Grão: cliente, na posição da data de referência (carteira analítica).
-- Faturamento dos 5 meses mais recentes (m0 = mês corrente, parcial), faixa de compra de cada
-- mês, média dos 3 meses fechados (m1 a m3), títulos, equipamentos cedidos e última compra.
with meses as (
    select
        {{ mes_int(data_referencia()) }} as m0,
        {% for k in range(1, 5) -%}
        {{ mes_int("cast(date_trunc('month', " ~ data_referencia() ~ ") - interval " ~ k ~ " month as date)") }} as m{{ k }}{% if not loop.last %},{% endif %}
        {% endfor %}
),

faturamento as (
    select
        f.cliente_id,
        {% for k in range(0, 5) -%}
        sum(f.valor_liquido) filter (where f.mes = m.m{{ k }}) as fat_m{{ k }},
        {% endfor -%}
        max(f.mes) filter (where f.valor_liquido > 0) as ultima_compra_mes
    from {{ ref('int_faturamento_cliente_mes') }} as f
    cross join meses as m
    group by f.cliente_id
),

equipamentos as (
    select
        cliente_id,
        sum(quantidade) filter (where tipo_equipamento = 'Geladeira vertical') as geladeira_vertical,
        sum(quantidade) filter (where tipo_equipamento = 'Freezer horizontal') as freezer_horizontal,
        sum(quantidade) filter (where tipo_equipamento = 'Carrinho térmico') as carrinho_termico,
        sum(quantidade) as equipamentos_total
    from {{ ref('stg_equipamentos_cedidos') }}
    group by cliente_id
),

base as (
    select
        c.cliente_id, c.revenda_id, r.revenda, c.razao_social, c.fantasia, c.canal, c.classe,
        c.cidade, c.bairro, va.vendedor_id,
        case when c.data_bloqueio <= {{ data_referencia() }} then 'Inativo' else 'Ativo' end as situacao,
        fin.valor_aberto, fin.valor_vencido, fin.vencimento_mais_antigo, fin.dias_debito_antigo, fin.semanas_atraso,
        coalesce(e.geladeira_vertical, 0) as geladeira_vertical,
        coalesce(e.freezer_horizontal, 0) as freezer_horizontal,
        coalesce(e.carrinho_termico, 0) as carrinho_termico,
        coalesce(e.equipamentos_total, 0) as equipamentos_total,
        f.fat_m0, f.fat_m1, f.fat_m2, f.fat_m3, f.fat_m4, f.ultima_compra_mes,
        round((coalesce(f.fat_m1, 0) + coalesce(f.fat_m2, 0) + coalesce(f.fat_m3, 0)) / 3, 2) as media_fat_3m
    from {{ ref('stg_clientes') }} as c
    inner join {{ ref('stg_revendas') }} as r on r.revenda_id = c.revenda_id
    inner join {{ ref('int_cliente_financeiro') }} as fin on fin.cliente_id = c.cliente_id
    left join {{ ref('int_cliente_vendedor_atual') }} as va on va.cliente_id = c.cliente_id
    left join equipamentos as e on e.cliente_id = c.cliente_id
    left join faturamento as f on f.cliente_id = c.cliente_id
)

select
    *,
    {% for k in range(0, 5) -%}
    {{ faixa_compra('fat_m' ~ k) }} as faixa_m{{ k }},
    {% endfor -%}
    case when valor_vencido > 0 then 'Inadimplente' else 'Adimplente' end as status_inadimplencia,
    case
        when valor_aberto = 0 then 'Sem títulos'
        when dias_debito_antigo = 0 then 'A vencer'
        when semanas_atraso >= 8 then '8+ semanas'
        when semanas_atraso = 1 then '1 semana'
        else cast(semanas_atraso as varchar) || ' semanas'
    end as faixa_atraso,
    round(media_fat_3m / nullif(equipamentos_total, 0), 2) as retorno_por_equipamento
from base
