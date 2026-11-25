-- Grão: revenda x mês x vendedor (vendedor 0 = meta da revenda, que não é a soma dos vendedores).
-- A meta de cada tipo é a soma das linhas META e AJUSTE da planilha.
select
    revenda_id,
    mes,
    vendedor_id,
    sum(case when tipo_meta = 'FATURAMENTO_IMEDIATO' then valor else 0 end) as meta_faturamento_imediato,
    sum(case when tipo_meta = 'FATURAMENTO_ABASTECIMENTO' then valor else 0 end) as meta_faturamento_abastecimento,
    sum(case when tipo_meta = 'CAIXAS_FABRICANTE_IMEDIATO' then valor else 0 end) as meta_caixas_fabricante_imediato,
    sum(case when tipo_meta = 'CAIXAS_FABRICANTE_ABASTECIMENTO' then valor else 0 end) as meta_caixas_fabricante_abastecimento,
    sum(case when tipo_meta = 'CLIENTES_POSITIVADOS' then valor else 0 end) as meta_clientes_positivados
from {{ ref('stg_metas_comerciais') }}
group by revenda_id, mes, vendedor_id
