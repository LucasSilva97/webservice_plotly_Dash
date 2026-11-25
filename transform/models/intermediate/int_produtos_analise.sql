-- Grão: produto. Só o que entra nas análises: ativo e de revenda (material de PDV fica fora).
select *
from {{ ref('stg_produtos') }}
where ativo
  and categoria <> 'Material PDV'
