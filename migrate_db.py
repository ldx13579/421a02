import sys
import os
from datetime import datetime
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Poll, VoteSession, RateLimit

def migrate_database():
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("  数据库迁移脚本")
        print("=" * 60)
        
        try:
            with db.engine.connect() as conn:
                conn.execute(text('SELECT 1 FROM vote_sessions LIMIT 1'))
                conn.commit()
            print("  [跳过] VoteSession 表已存在")
        except Exception:
            print("  [创建] 创建 VoteSession 表...")
            db.create_all()
            print("  [OK] VoteSession 表创建完成")
        
        try:
            with db.engine.connect() as conn:
                conn.execute(text('SELECT 1 FROM rate_limits LIMIT 1'))
                conn.commit()
            print("  [跳过] RateLimit 表已存在")
        except Exception:
            print("  [创建] 创建 RateLimit 表...")
            db.create_all()
            print("  [OK] RateLimit 表创建完成")
        
        try:
            with db.engine.connect() as conn:
                conn.execute(text('SELECT is_results_public FROM polls LIMIT 1'))
                conn.commit()
            print("  [跳过] is_results_public 字段已存在")
        except Exception:
            print("  [添加] 为 polls 表添加 is_results_public 字段...")
            try:
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE polls ADD COLUMN is_results_public BOOLEAN DEFAULT 1'))
                    conn.commit()
                print("  [OK] is_results_public 字段添加完成")
            except Exception as e:
                print(f"  [警告] 添加字段失败: {e}")
                print("  [提示] 如果使用的是旧版 SQLite，可能需要手动迁移或重建数据库")
        
        print("\n" + "=" * 60)
        print("  迁移完成！")
        print("=" * 60)
        print("\n注意事项:")
        print("  1. VoteSession 表用于防止重复投票，包含唯一约束。")
        print("  2. RateLimit 表用于持久化存储请求频率限制。")
        print("  3. is_results_public 字段控制结果页面是否公开。")
        print("\n如果遇到问题，可以:")
        print("  - 删除 voting.db 文件后重启服务器，数据库会自动重建")

if __name__ == '__main__':
    migrate_database()
