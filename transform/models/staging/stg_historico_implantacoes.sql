select
    cast(revenda_id as integer) as revenda_id,
    cast(cliente_id as integer) as cliente_id,
    cast(data_implantacao as date) as data_implantacao,
    classificacao,
    cast(prazo_dias_antes as integer) as prazo_dias_antes,
    cast(prazo_dias_depois as integer) as prazo_dias_depois,
    cast(media_atraso as double) as media_atraso,
    cast(faturamento_medio as double) as faturamento_medio,
    cast(limite_antes as double) as limite_antes,
    cast(limite_depois as double) as limite_depois
from {{ source('raw', 'historico_implantacoes') }}
