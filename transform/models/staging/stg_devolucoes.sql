select
    cast(devolucao_id as integer) as devolucao_id,
    cast(pedido_id as integer) as pedido_id,
    cast(revenda_id as integer) as revenda_id,
    cast(cliente_id as integer) as cliente_id,
    cast(produto_id as integer) as produto_id,
    cast(data_devolucao as date) as data_devolucao,
    cast(qtd_caixas as integer) as qtd_caixas,
    cast(valor as double) as valor
from {{ source('raw', 'devolucoes') }}
