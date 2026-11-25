-- Grão: cliente ativo (sem bloqueio até a data de referência). Consulta de limite e prazo.
-- Regras inventadas, com os parâmetros em dbt_project.yml:
--   novo prazo: título vencido há credito_dias_debito_avista dias ou mais -> à vista;
--               senão, média de atraso >= credito_media_atraso_reducao -> desce um degrau
--               (mais de 14 dias -> 14; de 8 a 14 -> 7; de 1 a 7 -> à vista).
--   limite sugerido: compras do prazo (faturamento médio mensal x prazo em dias / 30) x
--               (1 + acréscimo da classificação), arredondado para cima na escada_limite.
--               Fica 0 (à vista) se não há faturamento,
--               se há débito antigo, se o prazo atual é à vista ou se o novo prazo é à vista.
--   limite comprometido: valor em aberto acima do limite atual (saldo negativo).
with faturamento as (
    select cliente_id, sum(valor_liquido) / ({{ var('credito_janela_dias') }} / 30.0) as faturamento_medio_3m
    from {{ ref('int_vendas_dia') }}
    where data > {{ data_referencia() }} - {{ var('credito_janela_dias') }}
    group by cliente_id
),

historico as (
    select cliente_id,
           count(*) filter (where prazo_dias_depois < prazo_dias_antes) as qtd_reducoes_prazo,
           max(data_implantacao) as ultima_implantacao
    from {{ ref('stg_historico_implantacoes') }}
    group by cliente_id
),

solicitacoes as (
    select cliente_id,
           count(*) as qtd_solicitacoes,
           count(*) filter (where situacao = 'Em análise') as solicitacoes_em_analise
    from {{ ref('stg_solicitacoes_credito') }}
    group by cliente_id
),

base as (
    select
        c.cliente_id, c.revenda_id, r.revenda, c.razao_social, c.fantasia, c.tipo_pessoa, c.cidade,
        c.canal, c.classe, c.classificacao, va.vendedor_id, c.condicao_pagamento_id,
        cp.condicao_pagamento as prazo_atual, cp.prazo_dias,
        c.limite_credito as limite_atual,
        fin.valor_aberto, fin.valor_vencido, fin.vencimento_mais_antigo, fin.dias_debito_antigo,
        fin.media_atraso, fin.qtd_titulos_pagos,
        round(coalesce(f.faturamento_medio_3m, 0), 2) as faturamento_medio_3m,
        coalesce(h.qtd_reducoes_prazo, 0) as qtd_reducoes_prazo,
        h.ultima_implantacao,
        coalesce(s.qtd_solicitacoes, 0) as qtd_solicitacoes,
        coalesce(s.solicitacoes_em_analise, 0) as solicitacoes_em_analise
    from {{ ref('stg_clientes') }} as c
    inner join {{ ref('stg_revendas') }} as r on r.revenda_id = c.revenda_id
    inner join {{ ref('stg_condicoes_pagamento') }} as cp on cp.condicao_pagamento_id = c.condicao_pagamento_id
    inner join {{ ref('int_cliente_financeiro') }} as fin on fin.cliente_id = c.cliente_id
    left join {{ ref('int_cliente_vendedor_atual') }} as va on va.cliente_id = c.cliente_id
    left join faturamento as f on f.cliente_id = c.cliente_id
    left join historico as h on h.cliente_id = c.cliente_id
    left join solicitacoes as s on s.cliente_id = c.cliente_id
    where c.data_bloqueio is null or c.data_bloqueio > {{ data_referencia() }}
),

prazo as (
    select
        *,
        case
            when prazo_dias > 0 and dias_debito_antigo >= {{ var('credito_dias_debito_avista') }} then 0
            when prazo_dias > 0 and media_atraso >= {{ var('credito_media_atraso_reducao') }} then
                case when prazo_dias > 14 then 14 when prazo_dias > 7 then 7 else 0 end
        end as novo_prazo_dias,
        round(faturamento_medio_3m * prazo_dias / 30.0 * (1 + {{ acrescimo_classificacao('classificacao') }}), 2) as limite_calculado
    from base
),

limite as (
    select
        *,
        case
            when faturamento_medio_3m <= 0
              or dias_debito_antigo >= {{ var('credito_dias_debito_avista') }}
              or prazo_dias = 0
              or novo_prazo_dias = 0 then 0
            else {{ degrau_limite('limite_calculado') }}
        end as limite_sugerido
    from prazo
)

select
    cliente_id, revenda_id, revenda, razao_social, fantasia, tipo_pessoa, cidade, canal, classe,
    classificacao, vendedor_id, condicao_pagamento_id, prazo_atual, prazo_dias,
    novo_prazo_dias,
    {{ texto_prazo('novo_prazo_dias') }} as novo_prazo,
    vencimento_mais_antigo as debito_mais_antigo,
    dias_debito_antigo,
    media_atraso,
    qtd_titulos_pagos,
    faturamento_medio_3m,
    limite_atual,
    valor_aberto,
    valor_vencido,
    round(limite_atual - valor_aberto, 2) as saldo_limite,
    round(100 * valor_aberto / nullif(limite_atual, 0), 1) as perc_limite_utilizado,
    limite_atual > 0 and valor_aberto > limite_atual as limite_comprometido,
    limite_calculado,
    cast(limite_sugerido as double) as limite_sugerido,
    case when limite_sugerido = 0 then 'À vista' else 'R$ ' || replace(format('{:,}', cast(limite_sugerido as integer)), ',', '.') end as sugestao_limite,
    cast(limite_sugerido - limite_atual as double) as alteracao_limite,
    qtd_reducoes_prazo,
    ultima_implantacao,
    qtd_solicitacoes,
    solicitacoes_em_analise
from limite
