{% macro generate_schema_name(custom_schema_name, node) -%}
    {# Use exact schema names (staging, marts) without prefixing target schema #}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
