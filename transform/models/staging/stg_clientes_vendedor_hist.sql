select
    cast(cliente_id as integer) as cliente_id,
    cast(vendedor_id as integer) as vendedor_id,
    cast(vigente_desde as date) as vigente_desde
from {{ source('raw', 'clientes_vendedor_hist') }}
