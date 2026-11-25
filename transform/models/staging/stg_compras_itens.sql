select
    cast(nota_compra as integer) as nota_compra,
    cast(revenda_id as integer) as revenda_id,
    fabricante,
    cast(produto_id as integer) as produto_id,
    cast(data_emissao as date) as data_emissao,
    cast(data_entrada as date) as data_entrada,
    cast(qtd_caixas as integer) as qtd_caixas,
    cast(valor as double) as valor
from {{ source('raw', 'compras_itens') }}
