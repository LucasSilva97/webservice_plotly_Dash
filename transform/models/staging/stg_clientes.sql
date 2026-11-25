select
    cast(cliente_id as integer) as cliente_id,
    cast(revenda_id as integer) as revenda_id,
    razao_social,
    fantasia,
    tipo_pessoa,
    canal,
    classe,
    classificacao,
    cidade,
    bairro,
    cast(data_cadastro as date) as data_cadastro,
    cast(data_bloqueio as date) as data_bloqueio,
    cast(condicao_pagamento_id as integer) as condicao_pagamento_id,
    cast(limite_credito as double) as limite_credito
from {{ source('raw', 'clientes') }}
