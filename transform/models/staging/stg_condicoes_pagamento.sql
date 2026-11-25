select
    cast(condicao_pagamento_id as integer) as condicao_pagamento_id,
    descricao as condicao_pagamento,
    cast(dias as integer) as prazo_dias
from {{ source('raw', 'condicoes_pagamento') }}
