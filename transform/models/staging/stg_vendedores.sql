select
    cast(vendedor_id as integer) as vendedor_id,
    cast(revenda_id as integer) as revenda_id,
    nome as vendedor,
    ativo = 1 as ativo
from {{ source('raw', 'vendedores') }}
