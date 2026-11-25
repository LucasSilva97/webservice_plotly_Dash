{# Falha se alguma combinação das colunas do grão aparecer mais de uma vez. #}
{% test grao_unico(model, colunas) %}
select {{ colunas | join(', ') }}, count(*) as repeticoes
from {{ model }}
group by {{ colunas | join(', ') }}
having count(*) > 1
{% endtest %}
