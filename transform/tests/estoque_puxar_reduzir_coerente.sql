-- Estoque: puxar só abaixo do mínimo, reduzir só acima do máximo, zero dentro da faixa;
-- e o trânsito de cada produto bate com a soma das notas em trânsito.
with linhas as (
    select * from {{ ref('estoque_reposicao') }}
),

notas as (
    select revenda_id, produto_id, sum(qtd_caixas) as qtd
    from {{ ref('estoque_transito_notas') }}
    group by revenda_id, produto_id
)

select 'faixa' as falha, l.revenda_id, l.produto_id, l.periodo, l.base_estoque
from linhas as l
where (l.reduzir_puxar > 0 and l.saldo_caixas >= l.estoque_minimo)
   or (l.reduzir_puxar < 0 and l.saldo_caixas <= l.estoque_maximo)
   or (l.reduzir_puxar = 0 and (l.saldo_caixas < l.estoque_minimo or l.saldo_caixas > l.estoque_maximo))

union all

select 'transito', l.revenda_id, l.produto_id, l.periodo, l.base_estoque
from linhas as l
left join notas as n on n.revenda_id = l.revenda_id and n.produto_id = l.produto_id
where l.qtd_transito <> coalesce(n.qtd, 0)
