-- Grão: cliente x data de implantação. O que mudou em cada implantação mensal de limite e prazo.
select
    h.revenda_id,
    r.revenda,
    h.cliente_id,
    c.razao_social,
    c.cidade,
    c.canal,
    h.classificacao,
    h.data_implantacao,
    h.prazo_dias_antes,
    h.prazo_dias_depois,
    {{ texto_prazo('h.prazo_dias_antes') }} as prazo_antes,
    {{ texto_prazo('h.prazo_dias_depois') }} as prazo_depois,
    h.media_atraso,
    h.faturamento_medio,
    h.limite_antes,
    h.limite_depois,
    h.limite_depois - h.limite_antes as alteracao_limite,
    case
        when h.limite_depois > h.limite_antes then 'Aumento'
        when h.limite_depois < h.limite_antes then 'Redução'
        else 'Mantido'
    end as tipo_alteracao,
    h.prazo_dias_depois < h.prazo_dias_antes as reducao_prazo
from {{ ref('stg_historico_implantacoes') }} as h
inner join {{ ref('stg_clientes') }} as c on c.cliente_id = h.cliente_id
inner join {{ ref('stg_revendas') }} as r on r.revenda_id = h.revenda_id
