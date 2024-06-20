{{ name | escape | underline}}

.. currentmodule:: {{ module }}

.. autosummary::
   :toctree: {{ name }}
   :recursive:

   .. toctree::
      :maxdepth: -1

   {% block model_fields %}
   {% for field in model_fields %}
      ~{{ field }}
   {% endfor %}
   {% endblock %}

.. autopydantic_model:: {{ objname }}
   :members:
   :inherited-members: BaseModel
   :model-show-config-summary: False
   :model-show-json: False
   :model-show-validator-members: False
   :model-show-validator-summary: False
   :field-list-validators: False

   {% block methods %}
   {% if methods %}
   .. rubric:: {{ _('Methods') }}

   .. autosummary::
      :nosignatures:
   {% for item in methods %}
      {%- if not item.startswith('_') %}
      ~{{ name }}.{{ item }}
      {%- endif -%}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block attributes %}
   {% if attributes %}
   .. rubric:: {{ _('Attributes') }}

   .. autosummary::
   {% for item in attributes %}
      ~{{ name }}.{{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

