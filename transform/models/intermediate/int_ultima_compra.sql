-- Grão: revenda x produto. Data da última entrada de compra da fábrica (transferência não conta).
select
    revenda_id,
    produto_id,
    max(data_entrada) as ultima_compra
from {{ ref('stg_compras_itens') }}
where data_entrada <= {{ data_referencia() }}
group by revenda_id, produto_id
