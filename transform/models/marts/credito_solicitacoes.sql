-- Grão: solicitação de alteração de limite e/ou prazo (geradas e registradas pelo painel).
select
    s.solicitacao_id,
    s.revenda_id,
    r.revenda,
    s.cliente_id,
    c.razao_social,
    c.cidade,
    c.canal,
    c.classificacao,
    s.data_solicitacao,
    s.tipo,
    s.limite_atual,
    s.limite_solicitado,
    cp.condicao_pagamento as prazo_atual,
    {{ texto_prazo('s.prazo_solicitado_dias') }} as prazo_solicitado,
    fin.media_atraso,
    s.situacao,
    s.solicitante,
    s.observacao,
    s.origem
from {{ ref('stg_solicitacoes_credito') }} as s
inner join {{ ref('stg_clientes') }} as c on c.cliente_id = s.cliente_id
inner join {{ ref('stg_revendas') }} as r on r.revenda_id = s.revenda_id
inner join {{ ref('stg_condicoes_pagamento') }} as cp on cp.condicao_pagamento_id = c.condicao_pagamento_id
inner join {{ ref('int_cliente_financeiro') }} as fin on fin.cliente_id = s.cliente_id
