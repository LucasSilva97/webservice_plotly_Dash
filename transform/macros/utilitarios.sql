{# O schema configurado no modelo é usado como está (staging, intermediate, marts),
   sem o prefixo do schema do profile. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}{{ target.schema }}{%- else -%}{{ custom_schema_name | trim }}{%- endif -%}
{%- endmacro %}

{# "Hoje" da demonstração: fixo, para a reexecução dar o mesmo resultado. #}
{% macro data_referencia() -%}
    cast('{{ var("data_referencia") }}' as date)
{%- endmacro %}

{# Mês no formato inteiro AAAAMM. #}
{% macro mes_int(coluna) -%}
    (year({{ coluna }}) * 100 + month({{ coluna }}))
{%- endmacro %}

{# Converte texto pt-BR ('1.234,56', '+500,00', '-3.000,00') em número. #}
{% macro numero_br(coluna) -%}
    cast(replace(replace(replace(trim({{ coluna }}), '+', ''), '.', ''), ',', '.') as double)
{%- endmacro %}

{# Primeiro degrau da escada de limites maior ou igual ao valor; acima de todos, o topo. #}
{% macro degrau_limite(expressao) -%}
    coalesce(
        (select min(degrau) from (values
            {%- for v in var('escada_limite') %} ({{ v }}){% if not loop.last %},{% endif %}{% endfor %}
        ) as escada(degrau) where degrau >= {{ expressao }}),
        {{ var('escada_limite')[-1] }}
    )
{%- endmacro %}

{# Texto do prazo: 0 dias = 'À vista'. #}
{% macro texto_prazo(dias) -%}
    case when {{ dias }} is null then null when {{ dias }} = 0 then 'À vista' else cast({{ dias }} as varchar) || ' dias' end
{%- endmacro %}
