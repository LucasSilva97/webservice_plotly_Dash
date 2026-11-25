{# Faixa de compra do cliente no mês (cortes inventados). Intervalos fechados à esquerda. #}
{% macro faixa_compra(coluna) -%}
    case
        when coalesce({{ coluna }}, 0) <= 0 then 'Sem compra'
        when {{ coluna }} < 300 then 'Até R$ 300'
        when {{ coluna }} < 800 then 'R$ 300 a 800'
        when {{ coluna }} < 2000 then 'R$ 800 a 2.000'
        else 'Acima de R$ 2.000'
    end
{%- endmacro %}

{# Acréscimo do limite de crédito pela classificação do cliente (var credito_acrescimo_classificacao). #}
{% macro acrescimo_classificacao(coluna) -%}
    case {{ coluna }}
        {% for classe, acrescimo in var('credito_acrescimo_classificacao').items() -%}
        when '{{ classe }}' then {{ acrescimo }}
        {% endfor -%}
        else 0
    end
{%- endmacro %}
