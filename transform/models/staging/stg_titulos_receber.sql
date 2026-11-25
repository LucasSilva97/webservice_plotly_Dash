select
    cast(titulo_id as integer) as titulo_id,
    cast(pedido_id as integer) as pedido_id,
    cast(revenda_id as integer) as revenda_id,
    cast(cliente_id as integer) as cliente_id,
    cast(data_emissao as date) as data_emissao,
    cast(data_vencimento as date) as data_vencimento,
    cast(valor as double) as valor,
    cast(data_pagamento as date) as data_pagamento,
    cast(valor_pago as double) as valor_pago
from {{ source('raw', 'titulos_receber') }}
