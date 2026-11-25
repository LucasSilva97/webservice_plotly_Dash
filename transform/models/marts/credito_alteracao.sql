-- Grão: cliente a prazo com mudança proposta para a próxima implantação (limite e/ou prazo).
-- É a entrada do executor elt/credito_implantacao.py, que grava só no ERP local da demonstração.
-- Data da implantação: o próximo dia credito_dia_implantacao a partir da data de referência.
select
    c.cliente_id,
    c.revenda_id,
    c.classificacao,
    c.condicao_pagamento_id as condicao_atual_id,
    c.prazo_dias as prazo_atual_dias,
    coalesce(c.novo_prazo_dias, c.prazo_dias) as prazo_novo_dias,
    cp.condicao_pagamento_id as condicao_nova_id,
    c.limite_atual,
    c.limite_sugerido as limite_novo,
    c.media_atraso,
    c.faturamento_medio_3m,
    case
        when day({{ data_referencia() }}) <= {{ var('credito_dia_implantacao') }}
            then make_date(year({{ data_referencia() }}), month({{ data_referencia() }}), {{ var('credito_dia_implantacao') }})
        else cast(date_trunc('month', {{ data_referencia() }}) + interval 1 month as date) + ({{ var('credito_dia_implantacao') }} - 1)
    end as data_implantacao
from {{ ref('credito_clientes') }} as c
inner join {{ ref('stg_condicoes_pagamento') }} as cp
    on cp.prazo_dias = coalesce(c.novo_prazo_dias, c.prazo_dias)
where c.prazo_dias > 0
  and (c.limite_sugerido <> c.limite_atual or c.novo_prazo_dias is not null)
