select
    cast(revenda_id as integer) as revenda_id,
    cast(produto_id as integer) as produto_id,
    cast(data_contagem as date) as data_contagem,
    cast(qtd_contada as integer) as qtd_contada
from {{ source('raw', 'contagens_estoque') }}
