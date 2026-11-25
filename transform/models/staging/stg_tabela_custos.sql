select
    cast(revenda_id as integer) as revenda_id,
    cast(produto_id as integer) as produto_id,
    cast(replace(mes, '-', '') as integer) as mes,
    cast(custo_caixa as double) as custo_caixa
from {{ source('raw', 'tabela_custos') }}
