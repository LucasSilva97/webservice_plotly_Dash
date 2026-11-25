-- A planilha chega como texto pt-BR: '12.345,00' e ajustes assinados ('+5.000,00', '-3.000,00').
select
    cast(revenda as integer) as revenda_id,
    cast(replace(mes, '-', '') as integer) as mes,
    cast(vendedor as integer) as vendedor_id,
    tipo_meta,
    tipo_linha,
    {{ numero_br('valor') }} as valor
from {{ source('raw', 'metas_comerciais') }}
