select
    cast(pedido_id as integer) as pedido_id,
    cast(item as integer) as item,
    cast(produto_id as integer) as produto_id,
    tipo_item,
    cast(qtd_caixas as integer) as qtd_caixas,
    cast(valor as double) as valor
from {{ source('raw', 'pedido_itens') }}
