select
    cast(revenda_id as integer) as revenda_id,
    cast(produto_id as integer) as produto_id,
    cast(data_posicao as date) as data_posicao,
    cast(saldo_caixas as integer) as saldo_caixas
from {{ source('raw', 'estoque_saldos') }}
