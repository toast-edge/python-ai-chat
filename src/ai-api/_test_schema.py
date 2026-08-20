from database.pg_connector import PgConnector

pg = PgConnector({
    "host": "47.93.0.181",
    "port": 5432,
    "database": "personal_finance",
    "user": "readonly_user",
    "password": "readonly",
})

ok, msg = pg.test_connection()
print("连接:", ok, msg)

tables = ["alipay_bill", "alipay_bill_info", "wechat_pay_bill", "wechat_pay_bill_info"]
schema = pg.get_tables_schema(tables)

for t in tables:
    cols = schema[t]
    print(f"\n=== {t} ({len(cols)} 字段) ===")
    for c in cols:
        print(f"  {c['column']}  {c['type']}  nullable={c['nullable']}  default={c['default']}")