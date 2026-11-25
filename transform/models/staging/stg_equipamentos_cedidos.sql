select
    cast(cliente_id as integer) as cliente_id,
    tipo_equipamento,
    cast(quantidade as integer) as quantidade
from {{ source('raw', 'equipamentos_cedidos') }}
