-- Grão: pedido emitido na janela de credito_janela_dias dias (o detalhe "Pedidos" do cliente).
-- Atraso do pedido pago = pagamento - vencimento; do vencido em aberto = referência - vencimento.
select
    p.pedido_id,
    p.revenda_id,
    p.cliente_id,
    p.vendedor_id,
    p.data_emissao,
    p.valor_total,
    p.status,
    cp.condicao_pagamento as prazo,
    t.data_vencimento,
    case when t.data_pagamento <= {{ data_referencia() }} then t.data_pagamento end as data_pagamento,
    case
        when t.data_pagamento <= {{ data_referencia() }}
            then greatest(0, date_diff('day', t.data_vencimento, t.data_pagamento))
        when t.titulo_id is not null and t.data_vencimento < {{ data_referencia() }}
            then date_diff('day', t.data_vencimento, {{ data_referencia() }})
    end as dias_atraso,
    case
        when p.status = 'CANCELADO' then 'Cancelado'
        when p.status = 'BLOQUEADO' then 'Bloqueado'
        when t.titulo_id is null then 'À vista'
        when t.data_pagamento <= {{ data_referencia() }} then 'Pago'
        when t.data_vencimento < {{ data_referencia() }} then 'Vencido'
        else 'A vencer'
    end as situacao
from {{ ref('stg_pedidos') }} as p
inner join {{ ref('stg_condicoes_pagamento') }} as cp on cp.condicao_pagamento_id = p.condicao_pagamento_id
left join {{ ref('stg_titulos_receber') }} as t on t.pedido_id = p.pedido_id
where p.data_emissao > {{ data_referencia() }} - {{ var('credito_janela_dias') }}
  and p.data_emissao <= {{ data_referencia() }}
