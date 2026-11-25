select
    cast(produto_id as integer) as produto_id,
    descricao as produto,
    marca,
    fabricante,
    categoria,
    canal,
    cast(unidades_por_caixa as integer) as unidades_por_caixa,
    cast(litros_por_caixa as double) as litros_por_caixa,
    ativo = 1 as ativo
from {{ source('raw', 'produtos') }}
