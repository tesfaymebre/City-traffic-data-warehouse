{% macro format_time_window(start_column, end_column) %}
{#
  Format pNEUMA filename time tokens (HHMM) into a human-readable window.
  Example: 0830, 0900 -> '08:30 - 09:00'
#}
concat(
    substring({{ start_column }}::text, 1, 2),
    ':',
    substring({{ start_column }}::text, 3, 2),
    ' - ',
    substring({{ end_column }}::text, 1, 2),
    ':',
    substring({{ end_column }}::text, 3, 2)
)
{% endmacro %}
