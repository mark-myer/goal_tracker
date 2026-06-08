import json
import xmlrpc.client

from questlog.crypto import decrypt_value
from questlog.database import OdooConnection


def _replace_me_with_uid(value, uid):
    if isinstance(value, list):
        return [_replace_me_with_uid(item, uid) for item in value]
    if isinstance(value, str) and value == "me":
        return uid
    return value


def _auth(connection: OdooConnection):
    api_key = decrypt_value(connection.api_key)
    common = xmlrpc.client.ServerProxy(f"{connection.url}/xmlrpc/2/common")
    uid = common.authenticate(connection.db, connection.user, api_key, {})
    if not uid:
        raise ValueError("Unable to authenticate to Odoo")
    models = xmlrpc.client.ServerProxy(f"{connection.url}/xmlrpc/2/object")
    return uid, api_key, common, models


def test_connection(connection: OdooConnection) -> dict:
    uid, _api_key, common, _models = _auth(connection)
    version = common.version()
    return {"uid": uid, "version": version.get("server_version", "unknown")}


def browse_models(connection: OdooConnection) -> list[dict]:
    uid, api_key, _common, models = _auth(connection)
    return models.execute_kw(
        connection.db,
        uid,
        api_key,
        "ir.model",
        "search_read",
        [[]],
        {"fields": ["model", "name"], "limit": 200},
    )


def get_numeric_fields(connection: OdooConnection, model: str) -> list[str]:
    uid, api_key, _common, models = _auth(connection)
    fields = models.execute_kw(connection.db, uid, api_key, model, "fields_get", [], {"attributes": ["type"]})
    return sorted(
        [
            name
            for name, metadata in fields.items()
            if metadata.get("type") in {"integer", "float", "monetary"}
        ]
    )


def fetch_odoo_metric(
    connection: OdooConnection,
    model: str,
    domain_json: str,
    field: str,
    aggregate: str,
) -> float:
    uid, api_key, _common, models = _auth(connection)
    domain = _replace_me_with_uid(json.loads(domain_json or "[]"), uid)

    if aggregate == "count":
        return float(models.execute_kw(connection.db, uid, api_key, model, "search_count", [domain]))

    field_spec = f"{field}:{aggregate}"
    result = models.execute_kw(
        connection.db,
        uid,
        api_key,
        model,
        "read_group",
        [domain, [field_spec], []],
    )
    if not result:
        return 0.0
    return float(result[0].get(f"{field}_{aggregate}", 0.0))
