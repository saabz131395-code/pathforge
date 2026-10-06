"""Build (or refresh) the database from the YAML files in catalog/."""

import sys

from database.init_db import CatalogError, initialize_database

if __name__ == '__main__':
    try:
        db_path = initialize_database()
    except CatalogError as exc:
        sys.exit(f'Catalogue error: {exc}')
    print(f'Database ready: {db_path}')
