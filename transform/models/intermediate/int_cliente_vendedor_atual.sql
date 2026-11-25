-- Grão: cliente. Vendedor da carteira no último mês em que o cliente aparece.
select
    cliente_id,
    vendedor_id
from {{ ref('int_carteira_mensal') }}
qualify row_number() over (partition by cliente_id order by mes desc) = 1
