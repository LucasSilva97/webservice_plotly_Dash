select
    cast(solicitacao_id as integer) as solicitacao_id,
    cast(revenda_id as integer) as revenda_id,
    cast(cliente_id as integer) as cliente_id,
    cast(data_solicitacao as date) as data_solicitacao,
    tipo,
    cast(limite_atual as double) as limite_atual,
    cast(limite_solicitado as double) as limite_solicitado,
    cast(prazo_solicitado_dias as integer) as prazo_solicitado_dias,
    situacao,
    solicitante,
    observacao,
    origem
from {{ source('raw', 'solicitacoes_credito') }}
