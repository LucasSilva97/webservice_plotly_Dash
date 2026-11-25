select
    cast(nf_transferencia as integer) as nf_transferencia,
    cast(revenda_origem as integer) as revenda_origem,
    cast(revenda_destino as integer) as revenda_destino,
    cast(produto_id as integer) as produto_id,
    cast(data_emissao as date) as data_emissao,
    cast(data_entrada as date) as data_entrada,
    cast(qtd_caixas as integer) as qtd_caixas
from {{ source('raw', 'transferencias') }}
