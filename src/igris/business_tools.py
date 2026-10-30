"""Requirement-filtered recommendations only; no installer or service activator."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolOption:
    name: str
    need: str
    priority: int
    license_review: str
    local_adapter: str = 'none'


CATALOG = (
    ToolOption('n8n', 'workflows', 1, 'Sustainable Use; enterprise exceptions', 'local_contract_only'),
    ToolOption('Activepieces', 'workflows', 2, 'MIT core; enterprise exceptions'),
    ToolOption('InvoicePlane', 'invoicing', 3, 'MIT text; trademark restrictions'),
    ToolOption('Strapi', 'content', 4, 'MIT core; enterprise exceptions'),
    ToolOption('Bagisto', 'commerce', 5, 'MIT'),
    ToolOption('Medusa', 'commerce', 6, 'MIT core; enterprise exceptions'),
    ToolOption('Chatwoot', 'support', 7, 'MIT core; enterprise exceptions'),
    ToolOption('Twenty CRM', 'crm', 8, 'AGPLv3 with additional permission; MIT packages; commercial exceptions'),
    ToolOption('Formbricks', 'surveys', 9, 'AGPLv3 core; MIT packages; enterprise exceptions'),
    ToolOption('Plausible Analytics', 'analytics', 10, 'AGPLv3 root; inspect community distribution'),
    ToolOption('Appsmith', 'internal_apps', 11, 'Apache-2.0 root; edition audit required'),
    ToolOption('Budibase', 'internal_apps', 12, 'GPLv3 overall; MPL packages; BSL paid features'),
    ToolOption('Odoo', 'erp', 13, 'LGPLv3 community; other distributions not audited'),
    ToolOption('ERPNext', 'erp', 14, 'GPLv3 root'),
    ToolOption('Saleor', 'commerce', 15, 'BSD-3-Clause'),
    ToolOption('Coolify', 'hosting', 16, 'Apache-2.0 root; infrastructure costs separate'),
    ToolOption('Mautic', 'marketing', 17, 'GPLv3-or-later'),
    ToolOption('Directus', 'data_backend', 18, 'MSCL-1.0-GPL; permitted-purpose and license-key restrictions'),
    ToolOption('NocoDB', 'data_backend', 19, 'Sustainable Use; branch restrictions'),
    ToolOption('Akaunting', 'invoicing', 20, 'BSL-1.1; limited production grant, version-specific change date'),
)


def recommend(need):
    if type(need) is not str or need not in {t.need for t in CATALOG}:
        raise ValueError('A supported concrete business requirement is required.')
    return tuple({'name': t.name, 'license_review': t.license_review,
                  'adapter': t.local_adapter, 'activation_authorized': False,
                  'hardware_verified': False, 'expense_verified': False}
                 for t in sorted(CATALOG, key=lambda t: t.priority) if t.need == need)
