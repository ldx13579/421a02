import sqlite3
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, 'voting.db')

print(f"=== 数据库检查 ===")
print(f"数据库路径: {db_path}")
print(f"文件存在: {os.path.exists(db_path)}")

if not os.path.exists(db_path):
    print("数据库文件不存在！")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n=== 所有表 ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for t in tables:
    print(f"  - {t[0]}")

if ('vote_sessions',) in tables:
    print("\n=== vote_sessions 表结构 ===")
    cursor.execute("PRAGMA table_info(vote_sessions);")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col}")
    
    print("\n=== vote_sessions 索引 ===")
    cursor.execute("PRAGMA index_list(vote_sessions);")
    indexes = cursor.fetchall()
    for idx in indexes:
        print(f"\n  索引: {idx}")
        cursor.execute(f"PRAGMA index_info({idx[1]});")
        idx_info = cursor.fetchall()
        print(f"    列: {idx_info}")
        
        # 检查是否唯一
        if idx[2] == 1:
            print(f"    唯一约束: YES")
        else:
            print(f"    唯一约束: NO (普通索引)")

    print("\n=== 创建 vote_sessions 的原始 SQL ===")
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='vote_sessions';")
    sql = cursor.fetchone()
    if sql:
        print(f"  {sql[0]}")
    else:
        print("  无法获取")

    print("\n=== 检查 UniqueConstraint ===")
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name LIKE 'uq_%';")
    unique_indexes = cursor.fetchall()
    if unique_indexes:
        for idx in unique_indexes:
            print(f"  唯一索引: {idx[0]}")
    else:
        print("  ❌ 数据库中没有找到唯一索引！")
        print("  ❌ 这就是为什么并发投票能成功插入的原因！")

else:
    print("\n❌ vote_sessions 表不存在！")

conn.close()

print("\n=== 结论 ===")
print("如果数据库中没有 UNIQUE 约束，")
print("那么 INSERT 永远不会触发 IntegrityError，")
print("并发请求就会都成功插入！")
