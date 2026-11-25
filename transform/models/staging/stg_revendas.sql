select
    cast(revenda_id as integer) as revenda_id,
    nome as revenda,
    cidade,
    tipo as tipo_revenda
from {{ source('raw', 'revendas') }}
