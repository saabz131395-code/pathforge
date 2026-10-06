"""Home page extras (tips, tools, freelance steps) loaded from catalog/home.yaml."""

from __future__ import annotations

from functools import lru_cache

import yaml

from database.init_db import CATALOG_DIR, CatalogError

REQUIRED = {
    'tips': ('icon', 'title', 'text'),
    'tools': ('name', 'url', 'use', 'for'),
    'freelance_steps': ('title', 'text'),
}


@lru_cache(maxsize=1)
def load_home_content() -> dict[str, list[dict]]:
    with (CATALOG_DIR / 'home.yaml').open(encoding='utf-8') as handle:
        data = yaml.safe_load(handle) or {}
    for section, fields in REQUIRED.items():
        items = data.get(section)
        if not isinstance(items, list) or not items:
            raise CatalogError(f'home.yaml: expected a non-empty "{section}:" list')
        for index, item in enumerate(items, start=1):
            missing = [field for field in fields if not item.get(field)]
            if missing:
                raise CatalogError(f'home.yaml {section} item {index}: missing {", ".join(missing)}')
        if section == 'tools':
            for item in items:
                if not str(item['url']).startswith('https://'):
                    raise CatalogError(f'home.yaml tool "{item["name"]}": url must start with https://')
    return {section: data[section] for section in REQUIRED}
