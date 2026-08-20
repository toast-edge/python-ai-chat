import psycopg2

HOST = "47.93.0.181"
PORT = 5432
USER = "readonly_user"
PASSWORD = "readonly"


def try_connect(dbname):
    try:
        conn = psycopg2.connect(
            host=HOST, port=PORT, dbname=dbname,
            user=USER, password=PASSWORD, connect_timeout=8,
        )
        return conn, None
    except Exception as e:
        return None, str(e)


def list_databases(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT datname FROM pg_database "
        "WHERE datistemplate = false AND datallowconn = true "
        "ORDER BY datname"
    )
    return [r[0] for r in cur.fetchall()]


def list_tables(conn, schema="public"):
    cur = conn.cursor()
    cur.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
        "ORDER BY table_name",
        (schema,),
    )
    return [r[0] for r in cur.fetchall()]


# 1) 先尝试连接常见库名，找出能连上的那个
connected_db = None
conn = None
for db in ["postgres", "readonly_user", "defaultdb", "readonly"]:
    c, err = try_connect(db)
    if c is not None:
        connected_db = db
        conn = c
        print(f"[OK] 连接成功: db={db}")
        break
    else:
        print(f"[--] db={db} 失败: {err}")

if conn is None:
    print("\n未能连接，请确认数据库名 / 网络 / 白名单")
    raise SystemExit(1)

# 2) 列出可连数据库
try:
    dbs = list_databases(conn)
    print("可连接的数据库:", dbs)
except Exception as e:
    print("列出数据库失败:", e)

# 3) 列出当前库 public schema 的表
try:
    tables = list_tables(conn)
    print(f"\n库 {connected_db} 的 public 表 (共 {len(tables)} 张):")
    for t in tables:
        print("  -", t)
except Exception as e:
    print("列出表失败:", e)

# 4) 尝试列出每个可连库的 public 表（帮助定位业务库）
print("\n逐库探测 public 表:")
for db in dbs:
    c2, err = try_connect(db)
    if c2 is None:
        print(f"  [{db}] 连接失败: {err}")
        continue
    try:
        ts = list_tables(c2)
        print(f"  [{db}] {len(ts)} 张表: {ts[:20]}")
    except Exception as e:
        print(f"  [{db}] 列表面失败: {e}")
    finally:
        c2.close()

conn.close()
print("\n探测完成")