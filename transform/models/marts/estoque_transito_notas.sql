-- Grão: documento x produto em trânsito para a revenda (o detalhe do clique em "Em trânsito").
select
    t.revenda_id,
    t.produto_id,
    p.produto,
    t.tipo,
    t.documento,
    t.origem,
    t.data_emissao,
    t.qtd_caixas,
    t.dias_em_transito
from {{ ref('int_transito') }} as t
inner join {{ ref('int_produtos_analise') }} as p on p.produto_id = t.produto_id
