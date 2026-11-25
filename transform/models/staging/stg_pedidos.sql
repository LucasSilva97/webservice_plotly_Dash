select
    cast(pedido_id as integer) as pedido_id,
    cast(revenda_id as integer) as revenda_id,
    cast(cliente_id as integer) as cliente_id,
    cast(vendedor_id as integer) as vendedor_id,
    cast(data_emissao as date) as data_emissao,
    cast(condicao_pagamento_id as integer) as condicao_pagamento_id,
    status,
    cast(valor_total as double) as valor_total
from {{ source('raw', 'pedidos') }}
