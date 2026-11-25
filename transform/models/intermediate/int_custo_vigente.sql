-- Grão: revenda x produto. Custo do mês mais recente disponível até o mês de referência
-- (se o mês corrente ainda não tem custo, vale o último mês que tem).
select
    revenda_id,
    produto_id,
    mes as mes_custo,
    custo_caixa
from {{ ref('stg_tabela_custos') }}
where mes <= {{ mes_int(data_referencia()) }}
qualify row_number() over (partition by revenda_id, produto_id order by mes desc) = 1
