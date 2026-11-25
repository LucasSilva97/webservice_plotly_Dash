-- Crédito: saldo = limite - aberto; débito antigo leva o cliente a prazo para à vista (prazo e
-- limite); o novo prazo nunca é maior que o atual; o limite sugerido é um degrau da escada.
select 'saldo' as falha, cliente_id
from {{ ref('credito_clientes') }}
where abs(saldo_limite - (limite_atual - valor_aberto)) > 0.01

union all

select 'debito_antigo', cliente_id
from {{ ref('credito_clientes') }}
where prazo_dias > 0
  and dias_debito_antigo >= {{ var('credito_dias_debito_avista') }}
  and (novo_prazo_dias <> 0 or limite_sugerido <> 0)

union all

select 'prazo_maior', cliente_id
from {{ ref('credito_clientes') }}
where novo_prazo_dias > prazo_dias

union all

select 'fora_da_escada', cliente_id
from {{ ref('credito_clientes') }}
where limite_sugerido <> 0
  and limite_sugerido not in ({{ var('escada_limite') | join(', ') }})
